"""Runze valve control."""
import sys
sys.path.append('W:\\BS-Automated\\Miguel\\github\\flowchem\\flowchem_fork\\src')

import warnings
from enum import Enum
from dataclasses import dataclass
from loguru import logger
import aioserial

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.runze.runze_valve_component import (
    Runze6PortDistributionValve,
    Runze8PortDistributionValve,
    Runze10PortDistributionValve,
    Runze12PortDistributionValve,
    Runze16PortDistributionValve,
)
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import miguel
from flowchem.utils.exceptions import InvalidConfigurationError


class RunzeValveHeads(Enum):
    """5 different valve types can be used. 6, 8, 10, 12, 16 multi-position valves."""

    SIX_PORT_SIX_POSITION = "6"
    EIGHT_PORT_EIGHT_POSITION = "8"
    TEN_PORT_TEN_POSITION = "10"
    TWELVE_PORT_TWELVE_POSITION = "12"
    SIXTEEN_PORT_SIXTEEN_POSITION = "16"


@dataclass
class SV06Command:
    """Class representing a command for the SV-06 Multiport Selector Valve."""

    address: int  # Slave address
    function_code: str  # Function code based on the command type
    parameter: int = 0  # Parameters corresponding to the function code (2 bytes)
    additional_params: str = ""  # Additional parameters for factory commands
    is_factory_command: bool = False  # Flag to indicate if this is a factory command

    FRAME_HEADER: str = "CC"
    FRAME_END: str = "DD"

    def compile(self) -> str:
        if not self.is_factory_command:
            # Standard command format: 8 bytes
            base_command = (
                f"{self.FRAME_HEADER}"                     # Frame Header
                f"{self.address:02X}"                      # Address in hexadecimal (2 digits)
                f"{self.function_code}"                # Function code in hexadecimal (2 digits)
                f"{self.parameter & 0xFF:02X}"             # Low byte of parameter
                f"{(self.parameter >> 8) & 0xFF:02X}"      # High byte of parameter
                f"{self.FRAME_END}"                        # Frame End
            )
            checksum = sum(int(base_command[i:i+2], 16) for i in range(0, len(base_command), 2)) & 0xFFFF
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"                   # Low byte of checksum
                f"{(checksum >> 8) & 0xFF:02X}"            # High byte of checksum
            )
        else:
            # Factory command format: 14 bytes
            base_command = (
                f"{self.FRAME_HEADER}"
                f"{self.address:02X}"
                f"{self.function_code:02X}"
                f"{self.additional_params}"               
                f"{self.FRAME_END}"
            )
            checksum = sum(int(base_command[i:i+2], 16) for i in range(0, len(base_command), 2)) & 0xFFFF
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"
                f"{(checksum >> 8) & 0xFF:02X}"
            )

        return compiled_command


class RunzeValveIO:
    """Setup with serial parameters, low-level IO for SV-06 Multiport Selector Valve."""

    DEFAULT_CONFIG = {
        "timeout": 1,
        "baudrate": 9600,  # Default baudrate
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.AioSerial) -> None:
        """Initialize serial port for SV-06 valve."""
        self._serial = aio_port

    @classmethod
    def from_config(cls, config):
        """Create RunzeValveIO from config."""
        # Combine the default configuration with the user-provided configuration
        configuration = RunzeValveIO.DEFAULT_CONFIG | config

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the valve on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)


    async def _write_async(self, command: bytes):
        """Write a command to the pump."""
        await self._serial.write_async(command)
        logger.info(f"Command {command!r} sent!")

    async def _read_reply_async(self) -> str:
        """Read the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.info(f"Reply received: {reply_string}")
        logger.info(f"decode: {reply_string.decode('utf-8')}")
        return reply_string.decode("ascii")

    async def write_and_read_reply_async(self, command: SV06Command) -> str:
        """Send a command to the pump, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write_async(f"{command.compile()}\r".encode("ascii"))
        response = await self._read_reply_async()
        if not response:
            logger.warning("No response received from the valve!")

        return self.parse_response(response)

    def parse_response(self, response: str) -> str:
        ...
        return response


class RunzeValve(FlowchemDevice):
    """
    Control Runze multi position valves.
    """
    _io_instances: set[RunzeValveIO] = set()

    def __init__(
        self,
        valve_io: RunzeValveIO,
        name: str,
        address: int = 1,
        **config,
    ) -> None:
        super().__init__(name)

        # Create communication
        self.valve_io = valve_io
        RunzeValve._io_instances.add(self.valve_io)

        self.address = address

        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Runze",
            model="SV-06",
        )

    async def initialize(self):
        await super().initialize()

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        valve_component: FlowchemComponent
        match self.device_info.additional_info["valve-type"]:
            case RunzeValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Runze6PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.EIGHT_PORT_EIGHT_POSITION:
                valve_component = Runze8PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TEN_PORT_TEN_POSITION:
                valve_component = Runze10PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Runze12PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Runze16PortDistributionValve(
                    "distribution-valve", self
                )
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of HamiltonPumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        valveio = None
        for obj in RunzeValve._io_instances:
            # noinspection PyProtectedMember
            if obj._serial.port == config.get("port"):
                valveio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if valveio is None:
            # Remove ML600-specific keys to only have HamiltonPumpIO's kwargs
            config_for_valveio = {
                k: v
                for k, v in config.items()
                if k not in ("address", "name")
            }
            valveio = RunzeValveIO.from_config(config_for_valveio)

        return cls(
            valveio,
            address=config.get("address", 1),
            name=config.get("name", ""),
        )


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM5",
        "address": 1,
        "name": "runze_test",
    }
    v = RunzeValve.from_config(**conf)

    async def main(valve):
        """Test function."""
        command = SV06Command(
            address=1,
            function_code="44",
            parameter=2,
        )
        logger.info(f"Raw Command {command.compile()!r} !")
        await valve.valve_io.write_and_read_reply_async(command)

    asyncio.run(main(v))

    # logger.info(f"Raw Command {command.compile().encode("ascii")!r} !")
    # await valve.valve_io.write_and_read_reply_async(command)
    # valve.valve_io._serial.reset_input_buffer()
    # command = "CC013F0000DDE901"
    # logger.info(f"{command.compile()}\r".encode("ascii"))
    # await valve.valve_io._write_async(f"{command.compile()}\r".encode("ascii"))
    # await valve.valve_io._read_reply_async()
    # reply_string = await valve.valve_io._serial.readline_async()
    # logger.info(f"Reply received: {reply_string}")