"""
This module is used to control Vici Valco Universal Electronic Actuators.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from typing import Set

import aioserial
from flowchem.exceptions import InvalidConfiguration
from flowchem.units import flowchem_ureg
from loguru import logger
from models.valves.injection_valve import InjectionValve
from models.valves.injection_valve import InjectionValvePosition


@dataclass
class ViciCommand:
    """
    This class represent a command.
    Its bytes() method is transmitted to the valve.
    """

    command: str
    valve_id: Optional[int] = None
    value: str = ""
    reply_lines: int = 1

    def __str__(self):
        """String representation of the command used for logs."""
        address = str(self.valve_id) if self.valve_id is not None else ""
        return f"{address} {self.command}{self.value}"

    def __bytes__(self):
        """Byte representation of the command used for serial communication."""
        return str(self).encode("ascii")


class ViciValcoValveIO:
    """Setup with serial parameters, low level IO"""

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

        self._serial = aio_port

    @classmethod
    def from_config(cls, port, **serial_kwargs):
        """Create ViciValcoValveIO from config."""
        # Merge default serial settings with provided ones.
        configuration = dict(ViciValcoValveIO.DEFAULT_CONFIG, **serial_kwargs)

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfiguration(
                f"Could not open serial port {port} with configuration {configuration}"
            ) from serial_exception

        return cls(serial_object)

    async def _read_reply(self, lines: int) -> str:
        """Reads the valve reply from serial communication"""
        reply_string = ""
        for _ in range(lines):
            line = await self._serial.readline_async()
            reply_string += line.decode("ascii")

        if reply_string:
            logger.debug(f"Reply received: {reply_string}")
        else:
            raise InvalidConfiguration(
                "No response received from valve! Check valve address?"
            )

        return reply_string.rstrip()

    async def write_and_read_reply(self, command: ViciCommand) -> str:
        """
        Main ViciValcoValveIO method.
        Sends a command to the valve, read the replies and returns it, optionally parsed.
        """
        # Make sure input buffer is empty
        self._serial.reset_input_buffer()

        # Send command
        await self._serial.write_async(bytes(command))
        logger.debug(f"Command {command} sent!")

        if command.reply_lines == 0:
            return ""
        else:
            return await self._read_reply(command.reply_lines)

    @property
    def name(self) -> str:
        """This is used to provide a nice-looking default name to valve based on its serial connection."""
        try:
            return self._serial.name
        except AttributeError:
            return ""


class ViciValco(InjectionValve):
    """
    ViciValco injection valves.
    """

    # This class variable is used for daisy chains (i.e. multiple valves on the same serial connection). Details below.
    _io_instances: Set[ViciValcoValveIO] = set()
    # When several valves are daisy-chained on the same serial port, they need to all access the *same* Serial object,
    # because access to the serial port is exclusive by definition.
    # The mutable object _io_instances as class variable creates a shared state across all the instances.

    # Map generic position to device-specific ones.
    position_mapping = {"LOAD": "1", "INJECT": "2"}

    def __init__(
        self,
        valve_io: ViciValcoValveIO,
        address: Optional[int] = None,
        name: str = None,
    ):
        """
        Default constructor, needs an ViciValcoValveIO object. See from_config() class method for config-based init.
        Args:
            valve_io: An ViciValcoValveIO w/ serial connection to the daisy chain w/ target valve.
            address: number of valve in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """

        self.valve_io = valve_io
        ViciValco._io_instances.add(self.valve_io)

        # The valve name is used for logs and error messages.
        self.name = f"Valve {self.valve_io.name}:{address}" if name is None else name
        super().__init__(name)

        self.address = address

    @classmethod
    def from_config(cls, port: str, address: int, name: str = None, **serial_kwargs):
        """This class method is used to create instances via config file by the server for HTTP interface."""
        existing_io = [v for v in ViciValco._io_instances if v._serial.port == port]

        # If no existing serial object are available for the port provided, create a new one
        if existing_io:
            valve_io = existing_io.pop()
        else:
            valve_io = ViciValcoValveIO.from_config(port, **serial_kwargs)

        return cls(valve_io, address=address, name=name)

    async def initialize(self):
        """Must be called after init before anything else."""
        await super().initialize()

        # Learning positions is only needed if the valve head has been reinstalled.
        await self.learn_positions()

        # Homing implies moving to position 1.
        await self.home()

        # Test connectivity by querying the valve's firmware version
        firmware_version = await self.version()
        logger.info(f"Connected to {self.name} - FW ver.: {firmware_version}!")

    async def learn_positions(self) -> None:
        """Initialize valve only, there is no reply -> reply_lines = 0"""
        learn = ViciCommand(valve_id=self.address, command="LRN")
        await self.valve_io.write_and_read_reply(learn)

    async def home(self) -> None:
        """Initialize valve only: Move to Home position"""
        home = ViciCommand(valve_id=self.address, command="HM")
        await self.valve_io.write_and_read_reply(home)

        # This seems necessary to make sure move is finished
        await self.get_position()

    async def version(self) -> str:
        """Returns the current firmware version reported by the valve."""
        version = ViciCommand(valve_id=self.address, command="VR", reply_lines=5)
        return await self.valve_io.write_and_read_reply(version)

    async def get_position(self) -> InjectionValvePosition:
        """Represent the position of the valve."""
        current_pos = ViciCommand(valve_id=self.address, command="CP")
        valve_pos = await self.valve_io.write_and_read_reply(current_pos)

        return InjectionValvePosition(self._reverse_position_mapping[valve_pos])

    async def set_position(self, position: InjectionValvePosition | str):
        """Set valve position. Switches really quick and doesn't reply, so waiting does not make sense."""

        if isinstance(position, InjectionValvePosition):
            target_pos = self.position_mapping[position.name]
        elif position in self.position_mapping.values():
            target_pos = position
        else:
            raise ValueError(f"Position {position} is not valid.")

        valve_by_name_cw = ViciCommand(
            valve_id=self.address, command="GO", value=target_pos, reply_lines=0
        )
        await self.valve_io.write_and_read_reply(valve_by_name_cw)

    async def timed_toggle(self, injection_time: int):
        """Switch valve to a position for a given time."""

        delay = flowchem_ureg(injection_time).to("ms")
        set_delay = ViciCommand(
            valve_id=self.address, command="DT", value=delay.magnitude
        )
        await self.valve_io.write_and_read_reply(set_delay)

        time_toggle = ViciCommand(valve_id=self.address, command="TT")
        await self.valve_io.write_and_read_reply(time_toggle)

    def get_router(self):
        """Creates an APIRouter for this object."""
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/firmware-version", self.version, methods=["GET"])
        router.add_api_route("/initialize", self.home, methods=["PUT"])
        router.add_api_route("/position", self.get_position, methods=["GET"])
        router.add_api_route("/position", self.set_position, methods=["PUT"])
        router.add_api_route("/timed-toggle", self.set_position, methods=["PUT"])

        return router


if __name__ == "__main__":
    import asyncio

    valve1 = ViciValco.from_config(port="COM13", address=0, name="test1")
    asyncio.run(valve1.initialize())

    # Set position works with both strings and InjectionValvePosition
    asyncio.run(valve1.set_position(InjectionValvePosition.LOAD))
    asyncio.run(valve1.set_position("2"))
