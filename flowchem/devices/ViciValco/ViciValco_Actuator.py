"""
This module is used to control Vici Valco Universal Electronic Actuators.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import aioserial
from aioserial import SerialException

from flowchem.constants import InvalidConfiguration, ActuationError, DeviceError


@dataclass
class ViciProtocolCommandTemplate:
    """ Class representing a valve command and its expected reply, but without target valve number """

    command: str
    optional_parameter: str = ""

    def to_valve(
        self, address: int, command_value: str = "", argument_value: str = ""
    ) -> ViciProtocolCommand:
        """ Returns a Protocol11Command by adding to the template valve address and command arguments """
        return ViciProtocolCommand(
            target_valve_num=address,
            command=self.command,
            optional_parameter=self.optional_parameter,
            command_value=command_value,
            argument_value=argument_value,
        )


@dataclass
class ViciProtocolCommand(ViciProtocolCommandTemplate):
    """ Class representing a valve command and its expected reply """

    target_valve_num: Optional[int] = 1
    command_value: Optional[str] = None
    argument_value: Optional[str] = None

    def compile(self) -> bytes:
        """ Create actual command byte by prepending valve address to command and appending executing command. """

        assert self.target_valve_num in range(0, 11)
        if not self.command_value:
            self.command_value = ""

        compiled_command = (
            f"{self.target_valve_num}"
            f"{self.command}{self.command_value}"
        )

        if self.argument_value:
            compiled_command += f"{self.optional_parameter}{self.argument_value}"

        return (compiled_command + "\r").encode("ascii")


class ViciValcoValveIO:
    """ Setup with serial parameters, low level IO"""

    DEFAULT_CONFIG = {
        "timeout": 0.5,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.Serial):
        """
        Initialize communication on the serial port where the valves are located and initialize them
        Args:
            aio_port: aioserial.Serial() object
        """

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self._serial = aio_port

        # These will be set in initialize
        self.num_valve_connected = None
        self._initialized = False

    @classmethod
    def from_config(cls, config):
        """ Create ViciValcoValveIO from config. """
        # Merge default settings, including serial, with provided ones.
        configuration = dict(ViciValcoValveIO.DEFAULT_CONFIG, **config)

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except SerialException as e:
            raise InvalidConfiguration(f"Cannot connect to the valve on the port <{configuration.get('port')}>") from e

        return cls(serial_object)

    async def initialize(self, hw_initialization: bool = True):
        """ Ensure connection + initialize. """
        # This has to be run after each power cycle to assign addresses to valves
        self.num_valve_connected = await self.detect_valve_address()

        if hw_initialization:
            self._hw_init()

        self._initialized = True

    async def detect_valve_address(self) -> int:
        """ Detects number of valves connected. """
        try:
            await self._serial.write_async("*ID\r".encode("ascii"))
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

        reply = self._serial.readlines()
        n_valves = len(reply)
        if n_valves == 0:
            raise InvalidConfiguration(f"No valve found on {self._serial.port}")
        else:
            self.logger.debug(f"Found {len(reply)} valves on {self._serial.port}!")
            return len(reply)

    def _hw_init(self):
        """ Send to all valves the HW initialization command (i.e. homing) """
        self._serial.write("*HM\r".encode("ascii"))  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

    async def _write(self, command: bytes):
        """ Writes a command to the valve """
        if not self._initialized:
            raise DeviceError("Valve not initialized!\n"
                              "Have you called `initialize()` after object creation?")
        await self._serial.write_async(command)
        self.logger.debug(f"Command {repr(command)} sent!")

    async def _read_reply(self, lines) -> str:
        """ Reads the valve reply from serial communication """
        reply_string = ''
        for line in range(lines):
            a = ''
            a = await self._serial.readline_async()
            reply_string += a.decode("ascii")

        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        self._serial.reset_input_buffer()

    async def write_and_read_reply(self, command: ViciProtocolCommand, lines) -> str:
        """ Main ViciValcoValveIO method.
        Sends a command to the valve, read the replies and returns it, optionally parsed """
        self.reset_buffer()
        await self._write(command.compile())
        if lines:
            response = await self._read_reply(lines)

            if not response:
                raise InvalidConfiguration(
                    f"No response received from valve, check valve address! "
                    f"(Currently set to {command.target_valve_num})"
                )
            return response.rstrip()

    def write_and_read_reply_sync(self, command: ViciProtocolCommand, lines) -> str:
        """ Main ViciValcoValveIO method.
                Sends a command to the valve, read the replies and returns it, optionally parsed """
        self.reset_buffer()
        self._serial.write(command.compile())
        x = self._serial.readline()
        return x

    @property
    def name(self) -> str:
        """ This is used to provide a nice-looking default name to valves based on their serial connection. """
        try:
            return self._serial.name
        except AttributeError:
            return ""


class ViciValco:
    """"
    """

    # This class variable is used for daisy chains (i.e. multiple valves on the same serial connection). Details below.
    _io_instances = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several valves are daisy chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).
    # FYI it is a borg idiom https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html

    valve_position_name = {'A': 1, 'B': 2}

    def __init__(
        self,
        valve_io: ViciValcoValveIO,
        address: int = 0,
        name: str = None,
    ):
        """
        Default constructor, needs an ViciValcoValveIO object. See from_config() class method for config-based init.
        Args:
            valve_io: An ViciValcoValveIO w/ serial connection to the daisy chain w/ target valve.
            address: number of valve in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        # ViciValcoValveIO
        self.valve_io = valve_io
        ViciValco._io_instances.add(self.valve_io)  # See above for details.

        # valve address is the valve sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # The valve name is used for logs and error messages.
        self.name = f"Valve {self.valve_io.name}:{address}" if name is None else name

        self.log = logging.getLogger(__name__).getChild(__class__.__name__).getChild(self.name)

    @classmethod
    def from_config(cls, config):
        """ This class method is used to create instances via config file by the server for HTTP interface. """
        # Many valve can be present on the same serial port with different addresses.
        # This shared list of ViciValcoValveIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each valve from a
        # config file, as it is the case in the HTTP server.
        # ViciValcoValve_IO() manually instantiated are not accounted for.
        valveio = None
        for obj in ViciValco._io_instances:
            if obj._serial.port == config.get("port"):
                valveio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if valveio is None:
        # TODO check
            config_for_valveio = {k: v for k, v in config.items() if k not in ("address", "name")}
            valveio = ViciValcoValveIO.from_config(config_for_valveio)

        return cls(valveio, address=config.get("address"), name=config.get("name"))

    async def initialize(self):
        """ Must be called after init before anything else. """
        # Test connectivity by querying the valve's firmware version
        fw_cmd = ViciProtocolCommandTemplate(command="VR").to_valve(self.address)
        firmware_version = await self.valve_io.write_and_read_reply(fw_cmd, lines=5)
        self.log.info(f"Connected to Vici Valve {self.name} - FW version: {firmware_version}!")

    def send_command_and_read_reply_sync(        self,
        command_template: ViciProtocolCommandTemplate,
        command_value="",
        argument_value="",
        lines=1):
        """ Sends a command based on its template by adding valve address and parameters, returns reply """
        return self.valve_io.write_and_read_reply_sync(
            command_template.to_valve(self.address, command_value, argument_value), lines
        )

    async def send_command_and_read_reply(
        self,
        command_template: ViciProtocolCommandTemplate,
        command_value="",
        argument_value="",
        lines=1
    ) -> str:
        """ Sends a command based on its template by adding valve address and parameters, returns reply """
        return await self.valve_io.write_and_read_reply(
            command_template.to_valve(self.address, command_value, argument_value), lines
        )

    async def learn_valve_positions(self) -> None:
        """ Initialize valve only, there is no reply -> lines = 0 """
        await self.send_command_and_read_reply(ViciProtocolCommandTemplate(command="LRN"), lines=0)

    async def initialize_valve(self) -> None:
        """ Initialize valve only: Move to Home position """
        await self.send_command_and_read_reply(ViciProtocolCommandTemplate(command="HM"), lines=0)
        # seems necessary to make sure move is finished
        await self.get_valve_position()

    async def version(self) -> str:
        """ Returns the current firmware version reported by the valve. """

        return await self.send_command_and_read_reply(ViciProtocolCommandTemplate(command="VR"), lines=5)

    async def get_valve_position(self) -> int:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum. """
        valve_pos = await self.send_command_and_read_reply(ViciProtocolCommandTemplate(command="CP"))
        return ViciValco.valve_position_name[valve_pos[-1]]

    def set_valve_position_sync(self, target_position: int):
        """ Set valve position. Switches really quick and doesn't reply, so waiting does not make sense

        """
        valve_by_name_cw = ViciProtocolCommandTemplate(command="GO")
        self.send_command_and_read_reply_sync(valve_by_name_cw, command_value=str(target_position), lines=0)
        self.log.debug(f"{self.name} valve position set to {target_position}")

    async def set_valve_position(self, target_position: int):
        """ Set valve position. Switches really quick and doesn't reply, so waiting does not make sense

        """
        valve_by_name_cw = ViciProtocolCommandTemplate(command="GO")
        await self.send_command_and_read_reply(valve_by_name_cw, command_value=str(target_position), lines=0)
        self.log.debug(f"{self.name} valve position set to {target_position}")
        new_position = await self.get_valve_position()
        if not new_position == target_position:
            raise ActuationError

    def get_router(self):
        """ Creates an APIRouter for this object. """
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/firmware-version", self.version, methods=["GET"])
        router.add_api_route("/initialize/valve", self.initialize_valve, methods=["PUT"])
        router.add_api_route("/valve/position", self.get_valve_position, methods=["GET"])
        router.add_api_route("/valve/position", self.set_valve_position, methods=["PUT"])

        return router


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM13",
        "address": 0,
        "name": "test1",

    }
    valve1 = ViciValco.from_config(conf)

    asyncio.run(valve1.initialize_valve())

    asyncio.run(valve1.set_valve_position(2))

    asyncio.run(valve1.set_valve_position(1))


# Control Command List for reference, don't see much of a point to implement all these, especially since most don't return anything
#
# GO[nn]     - Move to nn position -> None
#
# HM         - Move to the first Position -> None
#
# CW[nn]     - Move Clockwise to nn Position ->
#
# CC[nn]     - Move Counter Clockwise to nn Position ->
#
# TO         - Toggle Position to Oposite ->
#
# TT         - Timed Toggle
#
# DT[nnnnn]  - Set Delay time for TT Command
#
# CP         - Returns Current Position -> [ADDRESS]CP[A|B]
#
# AM[n]      - Sets the Actuator Mode [1] Two Position With Stops, -> [ADDRESS]AM[1|2|3]
#
#              [2] Two Position Without Stops, [3] Multi Position
#
# SB[nnnnn]  - Set the Baud Rate to nnnnn -> [ADDRESS]SB[BAUDRATE:int]
#
# NP[nn]     - Set the Number of Positions to nn -> 0E2 NP Invalid
#
# SM[n]      - Set the Direction [F]orward, [R]everse, [A]uto 0E2 SM Invalid
#
# LRN        - Learn Stops Location -> None
#
# CNT[nnnnn] - Set Cycle Counter -> 0CNT10254
#
# VR[n]      - Firmware Version [] Main [1] Display [2] Interface -> 0Dec 15 2011 \n 015:02:20 \n 0UA_MAIN_CT
#
# ID[nn]     - Set Device ID nn=(0-9, A-Z) -> 0ID0
#
# [n]ID*     - Reset ID to none n=Current ID
#
# IFM[n]     - Interface Mode [0] No Response [1] limited response -> 0IFM0
#
#              [2] Extended Response
#
# LG[n]      - Legacy Response Mode [0] Off [1] On -> 0LG0
#
# /?         - Displays This List
