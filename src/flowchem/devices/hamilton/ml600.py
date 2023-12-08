"""Control Hamilton ML600 syringe pump via the protocol1/RNO+."""
from __future__ import annotations

import asyncio
import string
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aioserial
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.hamilton.ml600_pump import ML600Pump
from flowchem.devices.hamilton.ml600_valve import ML600Valve
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin

if TYPE_CHECKING:
    import pint


# i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}
# Note ':' is used for broadcast within the daisy chain.
PUMP_ADDRESS = dict(enumerate(string.ascii_lowercase[:16], start=1))


@dataclass
class Protocol1Command:
    """Class representing a pump command and its expected reply."""

    command: str
    target_pump_num: int = 1
    target_syringe: str = ""
    command_value: str = ""
    optional_parameter: str = ""
    parameter_value: str = ""
    execution_command: str = "R"  # Execute

    def compile(self) -> str:
        """Create actual command byte by prepending pump address to command and appending executing command."""
        compiled_command = (
            f"{PUMP_ADDRESS[self.target_pump_num]}"
            f"{self.target_syringe}"
            f"{self.command}{self.command_value}"
        )

        if self.parameter_value:
            compiled_command += f"{self.optional_parameter}{self.parameter_value}"

        return compiled_command + self.execution_command


class HamiltonPumpIO:
    """Setup with serial parameters, low level IO."""

    ACKNOWLEDGE = chr(6)
    NEGATIVE_ACKNOWLEDGE = chr(21)

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_ODD,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.SEVENBITS,
    }

    def __init__(self, aio_port: aioserial.Serial) -> None:
        """Initialize serial port, not pumps."""
        self._serial = aio_port
        self.num_pump_connected: int | None = (
            None  # Set by `HamiltonPumpIO.initialize()`
        )

    @classmethod
    def from_config(cls, config):
        """Create HamiltonPumpIO from config."""
        configuration = HamiltonPumpIO.DEFAULT_CONFIG | config

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the pump on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)

    async def initialize(self, hw_initialization: bool = True):
        """Ensure connection with pump and initialize it (if hw_initialization is True)."""
        self.num_pump_connected = await self._assign_pump_address()
        if hw_initialization:
            await self._hw_init()
        await self._is_single_syringe()

    async def _is_single_syringe(self):
        try:
            await self._write_async(b"aH\r")
        except aioserial.SerialException as e:
            raise InvalidConfigurationError from e

        reply = await self._read_reply_async()
        print(reply)
        try:
            await self._write_async(b"aHR\r")
        except aioserial.SerialException as e:
            raise InvalidConfigurationError from e

        reply = await self._read_reply_async()

        print(f"+R:{reply}")

    async def _assign_pump_address(self) -> int:
        """Auto assign pump addresses.

        To be run on init, auto assign addresses to pumps based on their position in the daisy chain.
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        try:
            await self._write_async(b"1a\r")
        except aioserial.SerialException as e:
            raise InvalidConfigurationError from e

        reply = await self._read_reply_async()
        if not reply or reply[:1] != "1":
            raise InvalidConfigurationError(f"No pump found on {self._serial.port}")
        # reply[1:2] should be the address of the last pump. However, this does not work reliably.
        # So here we enumerate the pumps explicitly instead
        last_pump = 0
        for pump_num, address in PUMP_ADDRESS.items():
            await self._write_async(f"{address}UR\r".encode("ascii"))
            if "NV01" in await self._read_reply_async():
                last_pump = pump_num
            else:
                break
        logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
        return int(last_pump)

    async def _hw_init(self):
        """Send to all pumps the HW initialization command (i.e. homing)."""
        await self._write_async(b":XR\r")  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

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

    def parse_response(self, response: str) -> str:
        """Split a received line in its components: status, reply."""
        status, reply = response[:1], response[1:]

        assert status in (self.ACKNOWLEDGE, self.NEGATIVE_ACKNOWLEDGE)
        if status == self.NEGATIVE_ACKNOWLEDGE:
            logger.warning("Negative acknowledge received")
            warnings.warn(
                "Negative acknowledge reply: check command syntax!",
                stacklevel=2,
            )

        return reply.rstrip()  # removes trailing <cr>

    async def write_and_read_reply_async(self, command: Protocol1Command) -> str:
        """Send a command to the pump, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write_async(f"{command.compile()}\r".encode("ascii"))
        response = await self._read_reply_async()

        if not response:
            raise InvalidConfigurationError(
                f"No response received from pump! "
                f"Maybe wrong pump address? (Set to {command.target_pump_num})"
            )

        return self.parse_response(response)


class ML600(FlowchemDevice):
    """ML600 implementation according to manufacturer docs. Tested on a 61501-01 (i.e. single syringe system).

    From manufacturer docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """

    DEFAULT_CONFIG = {
        "default_infuse_rate": "1 ml/min",
        "default_withdraw_rate": "1 ml/min",
    }

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances: set[HamiltonPumpIO] = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy-chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).

    # Only Hamilton syringes are compatible w/ the ML600, and they come on a limited set of sizes. (Values in ml)
    VALID_SYRINGE_VOLUME = {
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        25.0,
        50.0,
    }

    def __init__(
        self,
        pump_io: HamiltonPumpIO,
        syringe_volume: str,
        name: str,
        address: int = 1,
        **config,
    ) -> None:
        """Default constructor, needs an HamiltonPumpIO object. See from_config() class method for config-based init.

        Args:
        ----
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump.
            syringe_volume: Volume of the syringe used, either a Quantity or number in ml.
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Hamilton",
            model="ML600",
        )
        # HamiltonPumpIO
        self.pump_io = pump_io
        ML600._io_instances.add(self.pump_io)  # See above for details.

        # Pump address is the pump sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # Syringe pumps only perform linear movement, and the volume displaced is function of the syringe loaded.
        try:
            self.syringe_volume = ureg.Quantity(syringe_volume)
        except AttributeError as attribute_error:
            logger.error(f"Invalid syringe volume {syringe_volume}!")
            raise InvalidConfigurationError(
                "Invalid syringe volume provided."
                "The syringe volume is a string with units! e.g. '5 ml'"
            ) from attribute_error

        if self.syringe_volume.m_as("ml") not in ML600.VALID_SYRINGE_VOLUME:
            raise InvalidConfigurationError(
                f"The specified syringe volume ({syringe_volume}) is invalid!\n"
                f"The volume (in ml) has to be one of {ML600.VALID_SYRINGE_VOLUME}"
            )

        self._steps_per_ml = ureg.Quantity(f"{48000 / self.syringe_volume} step")
        self._offset_steps = 100  # Steps added to each absolute move command, to decrease wear and tear at volume = 0
        self._max_vol = (48000 - self._offset_steps) * ureg.step / self._steps_per_ml
        logger.warning(f"due to offset steps is {self._offset_steps}. the max_vol : {self._max_vol}")
        # This enables to configure on per-pump basis uncommon parameters
        self.config = ML600.DEFAULT_CONFIG | config

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of HamiltonPumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        pumpio = None
        for obj in ML600._io_instances:
            # noinspection PyProtectedMember
            if obj._serial.port == config.get("port"):
                pumpio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if pumpio is None:
            # Remove ML600-specific keys to only have HamiltonPumpIO's kwargs
            config_for_pumpio = {
                k: v
                for k, v in config.items()
                if k not in ("syringe_volume", "address", "name")
            }
            pumpio = HamiltonPumpIO.from_config(config_for_pumpio)

        return cls(
            pumpio,
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name", ""),
        )

    async def initialize(self, hw_init=False, init_speed: str = "200 sec / stroke"):
        """Initialize pump and its components."""
        await self.pump_io.initialize()
        # Test connectivity by querying the pump's firmware version
        fw_cmd = Protocol1Command(command="U", target_pump_num=self.address)
        self.device_info.version = await self.pump_io.write_and_read_reply_async(fw_cmd)
        logger.info(
            f"Connected to Hamilton ML600 {self.name} - FW version: {self.device_info.version}!",
        )

        if hw_init:
            await self.initialize_pump(speed=ureg.Quantity(init_speed))
        # Add device components
        self.components.extend([ML600Pump("pump", self), ML600Valve("valve", self)])

    async def send_command_and_read_reply(self, command: Protocol1Command) -> str:
        """Send a command to the pump. Here we just add the right pump number."""
        command.target_pump_num = self.address
        return await self.pump_io.write_and_read_reply_async(command)

    def _validate_speed(self, speed: pint.Quantity | None) -> str:
        """Validate the speed.

        Given a speed (seconds/stroke) returns a valid value for it, and a warning if out of bounds.
        """
        # Validated speeds are used as command argument, with empty string being the default for None
        if speed is None:
            return ""

        # Alert if out of bounds but don't raise exceptions, according to general philosophy.
        # Target flow rate too high
        if speed < ureg.Quantity("2 sec/stroke"):
            speed = ureg.Quantity("2 sec/stroke")
            warnings.warn(
                f"Desired speed ({speed}) is unachievable!"
                f"Set to {self._seconds_per_stroke_to_flowrate(speed)}"
                f"Wrong units? A bigger syringe is needed?",
                stacklevel=2,
            )

        # Target flow rate too low
        if speed > ureg.Quantity("3692 sec/stroke"):
            speed = ureg.Quantity("3692 sec/stroke")
            warnings.warn(
                f"Desired speed ({speed}) is unachievable!"
                f"Set to {self._seconds_per_stroke_to_flowrate(speed)}"
                f"Wrong units? A smaller syringe is needed?",
                stacklevel=2,
            )

        return str(round(speed.m_as("sec / stroke")))

    async def initialize_pump(self, speed: pint.Quantity | None = None):
        """Initialize both syringe and valve.

        speed: 2-3692 in seconds/stroke
        """
        init_pump = Protocol1Command(
            command="X",
            optional_parameter="S",
            parameter_value=self._validate_speed(speed),
        )
        return await self.send_command_and_read_reply(init_pump)

    # async def initialize_valve(self):
    #     """Initialize valve only."""
    #     return await self.send_command_and_read_reply(Protocol1Command(command="LX"))

    # async def initialize_syringe(self, speed: pint.Quantity | None = None):
    #     """
    #     Initialize syringe only.
    #
    #     speed: 2-3692 in seconds/stroke
    #     """
    #     init_syringe = Protocol1Command(
    #         command="X1",
    #         optional_parameter="S",
    #         parameter_value=self._validate_speed(speed),
    #     )
    #     return await self.send_command_and_read_reply(init_syringe)

    def flowrate_to_seconds_per_stroke(self, flowrate: pint.Quantity):
        """Convert flow rates to steps per seconds.

        To determine the volume dispensed per step the total syringe volume is divided by
        48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
        length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
        example to dispense 9 mL from a 10 mL syringe you would determine the number of
        steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
        """
        flowrate_in_steps_sec = flowrate * self._steps_per_ml
        return (1 / flowrate_in_steps_sec).to("second/stroke")

    def _seconds_per_stroke_to_flowrate(self, second_per_stroke) -> float:
        """Convert seconds per stroke to flow rate."""
        flowrate = 1 / (second_per_stroke * self._steps_per_ml)
        return flowrate.to("ml/min")

    def _volume_to_step_position(self, volume: pint.Quantity) -> int:
        """Convert a volume to a step position."""
        # noinspection PyArgumentEqualDefault
        steps = volume * self._steps_per_ml
        return round(steps.m_as("steps")) + self._offset_steps

    async def _to_step_position(
        self,
        position: int,
        speed: pint.Quantity | None = None,
    ):
        """Absolute move to step position."""
        abs_move_cmd = Protocol1Command(
            command="M",
            optional_parameter="S",
            command_value=str(position),
            parameter_value=self._validate_speed(speed),
        )
        return await self.send_command_and_read_reply(abs_move_cmd)

    async def get_current_volume(self) -> pint.Quantity:
        """Return current syringe position in ml."""
        syringe_pos = await self.send_command_and_read_reply(
            Protocol1Command(command="YQP"),
        )

        current_steps = (int(syringe_pos) - self._offset_steps) * ureg.step
        logger.info(current_steps)
        return current_steps / self._steps_per_ml

    async def to_volume(self, target_volume: pint.Quantity, rate: pint.Quantity):
        """Absolute move to volume provided."""
        speed = self.flowrate_to_seconds_per_stroke(rate)
        await self._to_step_position(
            self._volume_to_step_position(target_volume),
            speed,
        )
        logger.debug(f"Pump {self.name} set to volume {target_volume} at speed {speed}")

    async def pause(self):
        """Pause any running command."""
        return await self.send_command_and_read_reply(
            Protocol1Command(command="", execution_command="K"),
        )

    async def resume(self):
        """Resume any paused command."""
        return await self.send_command_and_read_reply(
            Protocol1Command(command="", execution_command="$"),
        )

    async def stop(self):
        """Stop and abort any running command."""
        await self.pause()
        return await self.send_command_and_read_reply(
            Protocol1Command(command="", execution_command="V"),
        )

    async def wait_until_idle(self) -> bool:
        """Return when no more commands are present in the pump buffer."""
        logger.debug(f"ML600 pump {self.name} wait until idle...")
        while not await self.is_idle():
            await asyncio.sleep(0.1)
        logger.debug(f"...ML600 pump {self.name} idle now!")
        return True

    async def version(self) -> str:
        """Return the current firmware version reported by the pump."""
        return await self.send_command_and_read_reply(Protocol1Command(command="U"))

    async def is_idle(self) -> bool:
        """Check if the pump is idle (actually check if the last command has ended)."""
        return (
            await self.send_command_and_read_reply(Protocol1Command(command="F", execution_command="")) == "Y"
        )

    async def get_valve_position(self) -> str:
        """Represent the position of the valve: getter returns Enum, setter needs Enum."""
        await self.send_command_and_read_reply(Protocol1Command(command="LQA"))
        return await self.send_command_and_read_reply(Protocol1Command(command="LQP"))

    async def set_valve_position(
        self,
        target_position: str,
        wait_for_movement_end: bool = True,
    ) -> bool:
        """Set valve position.

        wait_for_movement_end is defaulted to True as it is a common mistake not to wait...
        """
        await self.send_command_and_read_reply(
            Protocol1Command(command="LP0", command_value=target_position),
        )
        logger.debug(f"{self.name} valve position set to position {target_position}")
        if wait_for_movement_end:
            await self.wait_until_idle()
            return True

    # async def get_return_steps(self) -> int:
    #     """Return steps' getter. Applied to the end of a downward syringe movement to removes mechanical slack."""
    #     steps = await self.send_command_and_read_reply(Protocol1Command(command="YQN"))
    #     return int(steps)
    #
    # async def set_return_steps(self, target_steps: int):
    #     """Return steps' setter. Applied to the end of a downward syringe movement to removes mechanical slack."""
    #     target_steps = str(int(target_steps))
    #     return await self.send_command_and_read_reply(Protocol1Command(command="YSN", command_value=target_steps))


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM12",
        "address": 1,
        "name": "test1",
        "syringe_volume": 5,
    }
    pump1 = ML600.from_config(**conf)
    asyncio.run(pump1.initialize_pump())
