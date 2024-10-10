"""Runze SY-01B Syringe Pump control."""

import aioserial
import asyncio

from dataclasses import dataclass
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem import ureg
from flowchem.devices.runze.sy01b_valve import (
    SY01B_6PortDistributionValve,
    SY01B_9PortDistributionValve,
    SY01B_12PortDistributionValve,
)
from flowchem.devices.runze.sy01b_pump import SY01BPump
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import miguel
from flowchem.utils.exceptions import InvalidConfigurationError


@dataclass
class RunzeCommand:
    """Class representing a command for the SV-06 Multiport Selector Valve."""

    address: int  # Slave address
    function_code: str  # Function code based on the command type
    parameter: int = 0  # Parameters corresponding to the function code
    is_factory_command: bool = False  # Flag to indicate if this is a factory command

    password: str = "FFEEBBAA"
    FRAME_HEADER: str = "CC"
    FRAME_END: str = "DD"

    def compile(self) -> str:
        if not self.is_factory_command:
            # Standard command format: 8 bytes
            base_command = (
                f"{self.FRAME_HEADER}"                     
                f"{self.address:02X}"                      
                f"{self.function_code}"                
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
                f"{self.function_code}"
                f"{self.password}"
                f"{self.parameter:02X}000000"               
                f"{self.FRAME_END}"
            )
            checksum = sum(int(base_command[i:i+2], 16) for i in range(0, len(base_command), 2)) & 0xFFFF
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"
                f"{(checksum >> 8) & 0xFF:02X}"
            )

        return compiled_command


class RunzeIO:
    """Setup with serial parameters, low-level IO for Runze devices."""

    DEFAULT_CONFIG = {
        "timeout": 1,
        "baudrate": 9600,  #The corresponding baudrate can be set through a factory command (Possible baud rates: : 9600bps, 19200bps, 38400bps, 57600bps, 115200bps)
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.AioSerial) -> None:
        """Initialize serial port for SV-06 valve."""
        self._serial = aio_port

    @classmethod
    def from_config(cls, config):
        """Create RunzeIO from config."""
        # Combine the default configuration with the user provided configuration
        configuration = RunzeIO.DEFAULT_CONFIG | config

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the valve on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)

    async def _write_async(self, command: bytes):
        """Write a command to the valve."""
        await self._serial.write_async(command)

    async def _read_reply_async(self) -> str:
        """Read the valve reply from serial communication."""
        reply_string = await self._serial.readline_async()
        return reply_string.hex()

    async def write_and_read_reply_async(self, command: RunzeCommand, raise_errors: bool = True) -> tuple[str,str]:
        """Send a command to the valve, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write_async(bytes.fromhex(f"{command.compile()}\r"))
        response = await self._read_reply_async()
        if not response and raise_errors:
            raise InvalidConfigurationError(
                f"No response received from valve! "
                f"Maybe wrong valve address? (Set to {command.address})"
            )
        return self.parse_response(response=response, raise_errors=raise_errors)

    @staticmethod
    def parse_response(response: str, raise_errors: bool = True) -> tuple[str, str]:
        """Split a received line in its components: status, reply."""
        status, parameters = response[4:6], response[6:10]
        parameters = parameters[2:] + parameters[:2]  # The bytes are swapped in the reply
        status_strings = {
            "00": "Normal status",
            "01": "Frame error",
            "02": "Parameter error",
            "03": "Optocoupler error",
            "04": "Motor busy",
            "05": "Motor stalled",
            "06": "Unknown location",
            "fe": "Task suspension",
            "ff": "Unknown error"
        }

        status_string = status_strings.get(status, "Unknown status code")
        # Check if the status indicates an error
        if status in ("01", "02", "03", "04", "05", "06", "fe", "ff"):
            if raise_errors:
                logger.error(f"{status_string} (Status code: {status})")
                raise DeviceError(
                    f"{status_string} - Check command syntax or device status!"
                )
        return status_string, parameters


class SY01B(FlowchemDevice):
    """
    Control Runze SY01B Syringe Pump.
    """

    DEFAULT_CONFIG = {
        "default_infuse_rate": "1 ml/min",
        "default_withdraw_rate": "1 ml/min",
    }

    _io_instances: set[RunzeIO] = set()

    # volume in ml / diameter in mm
    VALID_SYRINGES = {
        0.025: 9.5,
        0.05: 9.5,
        0.125: 9.5,
        0.25: 9.5,
        0.5: 9.5,
        1.25: 13,
        2.5: 16.8,
        5.0: 20.5
    }

    def __init__(
        self,
        runze_io: RunzeIO,
        syringe_volume: str,
        name: str,
        address: int = 1,
        **config,
    ) -> None:
        super().__init__(name)

        # Create communication
        self.runze_io = runze_io
        SY01B._io_instances.add(self.runze_io)
        self.config = SY01B.DEFAULT_CONFIG | config
        self.address = int(address)
        self.max_count = 12000
        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Runze",
            model="SY-01B Syringe Pump",
        )

        try:
            self.syringe_volume = ureg.Quantity(syringe_volume)
            self.syringe_diameter = ureg.Quantity(f"{SY01B.VALID_SYRINGES[self.syringe_volume.m_as("ml")]} mm")
            self.max_flowrate = ureg.Quantity(f"{200 / ((self.max_count * self.syringe_volume.m_as("ml"))/10000)} ml/min")
        except AttributeError as attribute_error:
            logger.error(f"Invalid syringe volume {syringe_volume}!")
            raise InvalidConfigurationError(
                "Invalid syringe volume provided."
                "The syringe volume is a string with units! e.g. '5 ml'"
            ) from attribute_error

        if self.syringe_volume.m_as("ml") not in SY01B.VALID_SYRINGES.keys():
            raise InvalidConfigurationError(
                f"The specified syringe volume ({syringe_volume}) is invalid!\n"
                f"The volume (in ml) has to be one of {SY01B.VALID_SYRINGES.keys()}"
            )

        self._steps_per_ml = ureg.Quantity(f"{self.max_count / self.syringe_volume} steps")

    async def initialize(self):
        """Initialize pump and its components."""
        await self.reset_valve()
        await self.reset_syringe_pump()
        # Test connectivity by querying the pump's firmware version
        self.device_info.version = await self.get_current_version()
        logger.info(
            f"Connected to Runze SY-01B {self.name} - FW version: {self.device_info.version}!",
        )
        # ToDo: Get_valve_type()
        self.components.extend([SY01BPump("pump", self), SY01B_6PortDistributionValve("valve", self)])

    async def _send_command_and_read_reply(
            self,
            command: str,
            parameter: int = 0,
            raise_errors: bool = True,
            is_factory_command: bool =False,
    ):
        command = RunzeCommand(
            function_code=command,
            address=self.address,
            parameter=parameter,
            is_factory_command=is_factory_command,
        )
        status, parameters = await self.runze_io.write_and_read_reply_async(command, raise_errors)
        return status, parameters

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        runzeio = None
        for obj in SY01B._io_instances:
            # noinspection PyProtectedMember
            if obj._serial.port == config.get("port"):
                runzeio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if runzeio is None:
            # Remove RunzeValve-specific keys to only have RunzeeIO's configs
            config_for_runzeio = {
                k: v
                for k, v in config.items()
                if k not in ("syringe_volume", "address", "name")
            }
            runzeio = RunzeIO.from_config(config_for_runzeio)

        return cls(
            runzeio,
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name", ""),
        )

    def _flowrate_to_seconds_per_stroke(self, flowrate: ureg.Quantity):
        """Convert flow rates to steps per seconds.

        To determine the volume dispensed per step the total syringe volume is divided by
        6000 steps. All possible SY-01B Runze syringes are designed with a 30 mm stroke
        length designed to move 30 mm in 6,000 steps."""
        flowrate_in_steps_sec = flowrate * self._steps_per_ml
        return (1 / flowrate_in_steps_sec).to("second/stroke")

    def _seconds_per_stroke_to_flowrate(self, second_per_stroke) -> float:
        """Convert seconds per stroke to flow rate."""
        flowrate = 1 / (second_per_stroke * self._steps_per_ml)
        return flowrate.to("ml/min")

    def _volume_to_step_position(self, volume: ureg.Quantity) -> int:
        """Convert a volume to a step position."""
        steps = volume * self._steps_per_ml
        return round(steps.m_as("steps"))

    async def get_current_volume(self) -> ureg.Quantity:
        """Return current syringe position in ml."""
        status, steps = await self._send_command_and_read_reply(command="66")
        vol = int(steps, 16) / self._steps_per_ml.m_as("step / milliliter")
        return ureg.Quantity(f"{vol} ml")

    async def get_device_address(self) -> str:
        """Return current device address."""
        status, parameters = await self._send_command_and_read_reply(command="20")
        if status == "Normal status":
            logger.info(f"Current address is: {parameters}")
            return parameters

    async def set_device_address(self, address: int = None) -> str:
        """Sets current device address"""
        status, parameters = await self._send_command_and_read_reply(command="00", parameter=address)
        if status == "Normal status":
            logger.info(f"Device address set to: {parameters}")
            self.address = address
            return parameters

    async def reset_valve(self) -> str:
        """Resets the valve to the optocoupler."""
        status, parameters = await self._send_command_and_read_reply(command="4c")
        if status == "Normal status":
            logger.info(f"Valve ran to the reset optocoupler successfully")
            return parameters

    async def reset_syringe_pump(self) -> str:
        """Resets the syringe to home position."""
        status, parameters = await self._send_command_and_read_reply(command="4f", raise_errors=False)
        current_volume = await self.get_current_volume()
        if status == "Normal status" and current_volume == ureg.Quantity("0 ml"):
            logger.info(f"Syringe pump successfully ran to home position.")
            return parameters

    async def force_stop(self) -> str:
        """Resets the syringe to home position."""
        status, parameters = await self._send_command_and_read_reply(command="49")
        if status == "Normal status":
            logger.info(f"Syringe pump and valve stopped.")
            return parameters

    async def get_motor_status(self) -> str:
        """Resets the syringe to home position."""
        status, parameters = await self._send_command_and_read_reply(command="4a", raise_errors=False)
        return status

    async def set_flowrate(self, rate: ureg.Quantity) -> tuple[str,str]:
        """Sets the flowrate of the syringe."""
        speed = rate.m_as("ml/s") * (1 / (math.pi * ((self.syringe_diameter.m_as("cm")/2) ** 2))) * 10 * (1000 / (15 - 0.0333)) # ml/s * cm/cm^3 (length to volume) * mm/cm * speed/(mm/s)
        if speed <= 0:
            logger.warning(
                f"Desired rate ({rate}) is unachievable, please select a positive flowrate lower than {self.max_flowrate}!"
            )
            return "Parameter Error", ""

        if speed > 1000:
            logger.warning(
                     f"Desired rate ({rate}) is unachievable, please select a positive flowrate lower than {self.max_flowrate}!"
                 )
            return "Parameter Error", ""
        status, parameters = await self._send_command_and_read_reply(command="4b", parameter=int(speed))
        if status == "Normal status":
            logger.debug(f"Syringe pump speed set to {rate.m_as("ml/s")} ml/s.")
            return status, parameters

    async def set_absolute_volume(self, target_volume: ureg.Quantity) -> tuple[str,str]:
        """Absolute move to target volume provided by set step position and speed."""
        steps = target_volume.m_as("ml") * self._steps_per_ml.m_as("step / milliliter")
        status, parameters = await self._send_command_and_read_reply(command="4e", parameter=int(steps), raise_errors=False)
        await self.wait_until_system_idle()
        current_volume = await self.get_current_volume()
        #print(f"target_volume {target_volume.m_as("ml")}")
        #print(f"current_volume {current_volume.m_as("ml")}")
        if current_volume == target_volume:
            logger.debug(f"Syringe pump successfully set to volume {target_volume}.")
            return status, parameters

    async def set_syringe_volume(self, target_volume: ureg.Quantity, rate: ureg.Quantity) :
        """Absolute move to target volume provided by set step position and speed."""
        status, parameters = await self.set_flowrate(rate)
        if status == "Normal status":
            await self.set_absolute_volume(target_volume)

    async def set_raw_position(self, position: str) -> bool:
        """Resets the syringe to home position."""
        status, parameters = await self._send_command_and_read_reply(command="44", parameter=int(position))
        current_position = await self.get_raw_position()
        if status == "Normal status" and int(position) == int(current_position):
            logger.info(f"Syringe valve set to position: {current_position}.")
            return True

    async def get_raw_position(self) -> str:
        """Resets the syringe to home position."""
        status, parameters = await self._send_command_and_read_reply(command="ae")
        position = parameters[2:4]
        if status == "Normal status":
            logger.info(f"Syringe valve set to position: {position}.")
            return position

    async def wait_until_system_idle(self):
        """Return when no more commands are present in the pump buffer."""
        logger.debug(f"SY01B {self.name} wait until idle...")
        while not await self.is_system_idle():
            await asyncio.sleep(0.1)
        logger.debug(f"...SY01B {self.name} idle now!")
        return True

    async def is_system_idle(self) -> bool:
        """Check if the pump is idle (actually check if the last command has ended)."""
        status, parameters = await self._send_command_and_read_reply(command="4a", raise_errors=False)
        if status == "Normal status":
            return True

    async def get_current_version(self) -> str:
        """Check if the pump is idle (actually check if the last command has ended)."""
        status, parameters = await self._send_command_and_read_reply(command="3f", raise_errors=False)
        if status == "Normal status":
            return parameters


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM7",
        "syringe_volume": "5 ml",
        "address": 1,
        "name": "runze_test",
    }
    v = SY01B.from_config(**conf)


    async def main(valve):
        """Test function."""
        await v.set_syringe_volume(ureg.Quantity("4 ml"),ureg.Quantity("0.1 ml/s"))
        # status, response = await v._send_command_and_read_reply(command="66", parameter=00)
        # print(status)
        # print(response)
        #await v.set_absolute_volume(target_volume= ureg.Quantity("0 ml"))
        # print(f"max flowrate {v.max_flowrate}")

    asyncio.run(main(v))