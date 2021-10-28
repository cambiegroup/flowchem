from __future__ import annotations

import logging
import string
import warnings
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

import aioserial
from aioserial import SerialException

from flowchem.constants import InvalidConfiguration, ActuationError

@dataclass
class ViciProtocolCommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """

    command: str
    optional_parameter: str = ""

    def to_valve(
        self, address: int, command_value: str = "", argument_value: str = ""
    ) -> ViciProtocolCommand:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        return ViciProtocolCommand(
            target_valve_num=address,
            command=self.command,
            optional_parameter=self.optional_parameter,
            command_value=command_value,
            argument_value=argument_value,
        )


@dataclass
class ViciProtocolCommand(ViciProtocolCommandTemplate):
    """ Class representing a pump command and its expected reply """

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
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.Serial, hw_initialization: bool = True):
        """
        Initialize communication on the serial port where the pumps are located and initialize them
        Args:
            aio_port: aioserial.Serial() object
            hw_initialization: Whether each pumps has to be initialized. Note that this might be undesired!
        """

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self._serial = aio_port

        # This has to be run after each power cycle to assign addresses to pumps

        self.num_valve_connected = self.detect_valve_address()

        if hw_initialization:
            self._hw_init()

    @classmethod
    def from_config(cls, config):
        """ Create ViciValcoValveIO from config. """
        # Merge default settings, including serial, with provided ones.
        configuration = dict(ViciValcoValveIO.DEFAULT_CONFIG, **config)

        try:
            #configuration.pop("hw_initialization")
            serial_object = aioserial.AioSerial(**configuration)
        except SerialException as e:
            raise InvalidConfiguration(f"Cannot connect to the valve on the port <{configuration.get('port')}>") from e

        return cls(serial_object, config.get("hw_initialization", True))

    def detect_valve_address(self) -> int:
        """
        """
        try:
            self._serial.write("*ID\r".encode("ascii"))  # Do not use async here as it is called during init()
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

        try:

            reply = self._serial.readlines()
            1/len(reply)
            self.logger.debug(f"Found {len(reply)} pumps on {self._serial.port}!")
            return len(reply)

        except ZeroDivisionError:
            raise InvalidConfiguration(f"No pump found on {self._serial.port}")

    def _hw_init(self):
        """ Send to all valves the HW initialization command (i.e. homing) """
        self._serial.write("*GO1\r".encode("ascii"))  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

    def _write(self, command: bytes):
        """ Writes a command to the valve """
        self._serial.write(command)
        self.logger.debug(f"Command {repr(command)} sent!")

    async def _write_async(self, command: bytes):
        """ Writes a command to the valve """
        await self._serial.write_async(command)
        self.logger.debug(f"Command {repr(command)} sent!")

    def _read_reply(self) -> str:
        """ Reads the valve reply from serial communication """
        reply_string = self._serial.readline()
        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string.decode("ascii")

    async def _read_reply_async(self) -> str:
        """ Reads the valve reply from serial communication """
        reply_string = await self._serial.readline_async()
        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string.decode("ascii")

    def parse_response(self, response: str) -> str:
        """ Split a received line in its components: success, reply """
        # response is only expected for some commands implement that
        return response.rstrip()

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        self._serial.reset_input_buffer()

    def write_and_read_reply(self, command: ViciProtocolCommand) -> str:
        """ Sends a command to the pump, read the replies and returns it, optionally parsed """
        self.reset_buffer()
        self._write(command.compile())
        response = self._read_reply()

        if not response:
            raise InvalidConfiguration(
                f"No response received from pump, check pump address! "
                f"(Currently set to {command.target_valve_num})"
            )

        return self.parse_response(response)

    async def write_and_read_reply_async(self, command: ViciProtocolCommand) -> str:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        self.reset_buffer()
        await self._write_async(command.compile())
        response = await self._read_reply_async()

        if not response:
            raise InvalidConfiguration(
                f"No response received from pump, check pump address! "
                f"(Currently set to {command.target_valve_num})"
            )

        return self.parse_response(response)

    def write_wo_reply(self, command: ViciProtocolCommand) -> None:
        """ Sends a command to the valve and doesn't read reply (a lot of commands don't yield replies)"""
        self.reset_buffer()
        self._write(command.compile())

    async def write_wo_reply_async(self, command: ViciProtocolCommand) -> None:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        self.reset_buffer()
        await self._write_async(command.compile())


    @property
    def name(self) -> str:
        """ This is used to provide a nice-looking default name to pumps based on their serial connection. """
        try:
            return self._serial.name
        except AttributeError:
            return ""

class ViciValco:
    """"
    """

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy chained on the same serial port, they need to all access the same Serial object,
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
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        # ViciValcoValveIO
        self.valve_io = valve_io
        ViciValco._io_instances.add(self.valve_io)  # See above for details.

        # Pump address is the pump sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # The pump name is used for logs and error messages.
        self.name = f"Valve {self.valve_io.name}:{address}" if name is None else name

        # Syringe pumps only perform linear movement, and the volume displaced is function of the syringe loaded.

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # Test connectivity by querying the pump's firmware version
        fw_cmd = ViciProtocolCommandTemplate(command="VR").to_valve(self.address)
        firmware_version = self.valve_io.write_and_read_reply(fw_cmd)
        self.log.info(f"Connected to Vici Valve {self.name} - FW version: {firmware_version}!")

    @classmethod
    def from_config(cls, config):
        """ This class method is used to create instances via config file by the server for HTTP interface. """
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of HamiltonPumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        # HamiltonPump_IO() manually instantiated are not accounted for.
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

    async def send_command_and_read_reply(
        self,
        command_template: ViciProtocolCommandTemplate,
        command_value="",
        argument_value="",
    ) -> str:
        """ Sends a command based on its template by adding pump address and parameters, returns reply """
        return await self.valve_io.write_and_read_reply_async(
            command_template.to_valve(self.address, command_value, argument_value)
        )


    async def send_command_wo_reply(
        self,
        command_template: ViciProtocolCommandTemplate,
        command_value="",
        argument_value="",
    ) -> None:
        """ Sends a command based on its template by adding pump address and parameters"""
        await self.valve_io.write_wo_reply_async(
            command_template.to_valve(self.address, command_value, argument_value)
        )

    async def learn_valve_positions(self) -> None:
        """ Initialize valve only """
        await self.send_command_wo_reply(ViciProtocolCommandTemplate(command="LRN"))

    async def initialize_valve(self) -> None:
        """ Initialize valve only: Move to Home position """
        await self.send_command_wo_reply(ViciProtocolCommandTemplate(command="HM"))
        # seems necessary to make sure move is finished
        await self.get_valve_position()


    async def version(self) -> str:
        """ Returns the current firmware version reported by the pump. """

        first_line = await self.send_command_and_read_reply(ViciProtocolCommandTemplate(command="VR"))
        empty = self.valve_io._read_reply_async()
        second_line = self.valve_io._read_reply_async()
        empty = self.valve_io._read_reply_async()
        third_line = await self.valve_io._read_reply_async()
        return ''.join((first_line, second_line, third_line))

    async def get_valve_position(self) -> int:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum. """
        valve_pos = await self.send_command_and_read_reply(ViciProtocolCommandTemplate(command="CP"))
        return ViciValco.valve_position_name[valve_pos[-1]]

    async def set_valve_position(self, target_position: int):
        """ Set valve position. Switches really quick and doesn't reply, so waiting does not make sense

        """
        valve_by_name_cw = ViciProtocolCommandTemplate(command="GO")
        await self.send_command_wo_reply(valve_by_name_cw, command_value=str((target_position)))
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