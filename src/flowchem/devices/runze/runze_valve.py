"""Runze valve control."""
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
    RunzeInjectionValve,
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

    address: int  # Slave address (0x00 to 0xFF)
    function_code: int  # Function code based on the command type
    parameter: int = 0  # Parameters corresponding to the function code (2 bytes)
    additional_params: bytes = b""  # Additional parameters for factory commands
    is_factory_command: bool = False  # Flag to indicate if this is a factory command

    FRAME_HEADER: int = 0xCC
    FRAME_END: int = 0xDD

    def compile(self) -> bytes:
        """Compile the command into bytes format to be sent over the communication interface."""
        if not self.is_factory_command:
            # Standard command format: 8 bytes
            command_bytes = bytearray(8)
            command_bytes[0] = self.FRAME_HEADER
            command_bytes[1] = self.address
            command_bytes[2] = self.function_code
            command_bytes[3] = self.parameter & 0xFF  # Low byte of parameter
            command_bytes[4] = (self.parameter >> 8) & 0xFF  # High byte of parameter
            command_bytes[5] = self.FRAME_END
            checksum = sum(command_bytes[:6]) & 0xFFFF
            command_bytes[6] = checksum & 0xFF  # Low byte of checksum
            command_bytes[7] = (checksum >> 8) & 0xFF  # High byte of checksum
        else:
            # Factory command format: 14 bytes
            command_bytes = bytearray(14)
            command_bytes[0] = self.FRAME_HEADER
            command_bytes[1] = self.address
            command_bytes[2] = self.function_code
            command_bytes[3:7] = self.additional_params  # 4 bytes for parameters
            command_bytes[7] = self.FRAME_END
            checksum = sum(command_bytes[:12]) & 0xFFFF
            command_bytes[12] = checksum & 0xFF  # Low byte of checksum
            command_bytes[13] = (checksum >> 8) & 0xFF  # High byte of checksum

        return bytes(command_bytes)


class RunzeValveIO:
    """Setup with serial parameters, low-level IO for SV-06 Multiport Selector Valve."""

    DEFAULT_CONFIG = {
        "timeout": 1.0,  # Adjusted for SV-06, might need more time than the pump
        "baudrate": 9600,  # Default baudrate
        "parity": aioserial.PARITY_NONE,  # Assuming no parity unless specified
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.AioSerial) -> None:
        """Initialize serial port for SV-06 valve."""
        self._serial = aio_port

    @classmethod
    def from_config(cls, config):
        """Create SV06ValveIO from config."""
        # Combine the default configuration with the user-provided configuration
        configuration = cls.DEFAULT_CONFIG | config

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
        """
        Args:
        ----
            valve_io: A RunzeValveIO object
            address: Address of the valve in the daisy chain, default is 1.
            name: Name of the valve
        """
        super().__init__(name)
        self.eol = b"\r\n"
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







if __name__ == "__main__":
    import asyncio

    v = RunzeValve()

    async def main(valve):
        """Test function."""
        await valve.initialize()
        await valve.set_raw_position("I")
        print(await valve.get_raw_position())
        await valve.set_raw_position("L")
        print(await valve.get_raw_position())

    asyncio.run(main(v))