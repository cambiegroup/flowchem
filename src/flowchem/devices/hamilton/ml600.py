"""This module is used to control Hamilton ML600 syringe pump via the protocol1/RNO+."""
from __future__ import annotations

import string
import time
import warnings
from dataclasses import dataclass
from enum import IntEnum

import aioserial
from loguru import logger

from flowchem import ureg
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.exceptions import InvalidConfiguration
from flowchem.people import *


class ML600(FlowchemDevice):
    """ML600 implementation according to manufacturer docs. Tested on a 61501-01 (i.e. single syringe system).

    From manufacturer docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """

    metadata = DeviceInfo(
        authors=[dario, jakob, wei_hsin],
        maintainers=[dario],
        manufacturer="Hamilton",
        model="ML600",
    )

    @dataclass
    class Protocol1CommandTemplate:
        """Class representing a pump command and its expected reply, but without target pump number."""

        command: str
        optional_parameter: str = ""
        execute_command: bool = True

        def to_pump(
            self, address: int, command_value: str = "", argument_value: str = ""
        ) -> ML600.Protocol1Command:
            """Return a Protocol11Command by adding to the template pump address and command arguments."""
            return ML600.Protocol1Command(
                target_pump_num=address,
                command=self.command,
                optional_parameter=self.optional_parameter,
                command_value=command_value,
                argument_value=argument_value,
                execute_command=self.execute_command,
            )

    @dataclass
    class Protocol1Command(Protocol1CommandTemplate):
        """Class representing a pump command and its expected reply."""

        PUMP_ADDRESS = dict(enumerate(string.ascii_lowercase[:16], start=1))
        # i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}
        # Note ':' is used for broadcast within the daisy chain.

        target_pump_num: int = 1
        command_value: str | None = None
        argument_value: str | None = None

        def compile(self) -> bytes:
            """Create actual command byte by prepending pump address to command and appending executing command."""
            assert self.target_pump_num in range(1, 17)
            if not self.command_value:
                self.command_value = ""

            compiled_command = (
                f"{self.PUMP_ADDRESS[self.target_pump_num]}"
                f"{self.command}{self.command_value}"
            )

            if self.argument_value:
                compiled_command += f"{self.optional_parameter}{self.argument_value}"
            # Add execution flag at the end
            if self.execute_command is True:
                compiled_command += "R"

            return (compiled_command + "\r").encode("ascii")

    class HamiltonPumpIO:
        """Setup with serial parameters, low level IO."""

        ACKNOWLEDGE = chr(6)
        NEGATIVE_ACKNOWLEDGE = chr(21)
        DEFAULT_CONFIG = {
            "timeout": 0.1,
            "baudrate": 9600,
            "parity": aioserial.PARITY_EVEN,
            "stopbits": aioserial.STOPBITS_ONE,
            "bytesize": aioserial.SEVENBITS,
        }

        def __init__(self, aio_port: aioserial.Serial):
            """
            Initialize communication on the serial port where the pumps are located and initialize them.

            Args:
                aio_port: aioserial.Serial() object
            """
            self._serial = aio_port

            # These will be set by `HamiltonPumpIO.initialize()`
            self._initialized = False
            self.num_pump_connected: int | None = None

        @classmethod
        def from_config(cls, config):
            """Create HamiltonPumpIO from config."""
            # Merge default settings, including serial, with provided ones.
            configuration = ML600.HamiltonPumpIO.DEFAULT_CONFIG | config

            try:
                serial_object = aioserial.AioSerial(**configuration)
            except aioserial.SerialException as serial_exception:
                raise InvalidConfiguration(
                    f"Cannot connect to the pump on the port <{configuration.get('port')}>"
                ) from serial_exception

            return cls(serial_object)

        async def initialize(self, hw_initialization: bool = True):
            """
            Ensure connection with pump + initialize.

            Args:
                hw_initialization: Whether each pump has to be initialized. Note that this might be undesired!
            """
            # This has to be run after each power cycle to assign addresses to pumps
            self._initialized = True
            self.num_pump_connected = await self._assign_pump_address()
            if hw_initialization:
                await self._hw_init()

        async def _assign_pump_address(self) -> int:
            """
            Auto assign pump addresses.

            To be run on init, auto assign addresses to pumps based on their position in the daisy chain.
            A custom command syntax with no addresses is used here so read and write has been rewritten
            """
            try:
                await self._write_async(b"1a\r")
            except aioserial.SerialException as e:
                raise InvalidConfiguration from e

            reply = await self._read_reply_async()
            if not reply or reply[:1] != "1":
                raise InvalidConfiguration(f"No pump found on {self._serial.port}")
            # reply[1:2] should be the address of the last pump. However, this does not work reliably.
            # So here we enumerate the pumps explicitly instead
            last_pump = 0
            for pump_num, address in ML600.Protocol1Command.PUMP_ADDRESS.items():
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
            logger.debug(f"Command {repr(command)} sent!")

        async def _read_reply_async(self) -> str:
            """Read the pump reply from serial communication."""
            reply_string = await self._serial.readline_async()
            logger.debug(f"Reply received: {reply_string}")
            return reply_string.decode("ascii")

        @staticmethod
        def parse_response(response: str) -> str:
            """Split a received line in its components: success, reply."""
            status = response[:1]
            assert status in (
                ML600.HamiltonPumpIO.ACKNOWLEDGE,
                ML600.HamiltonPumpIO.NEGATIVE_ACKNOWLEDGE,
            ), "Invalid status reply!"

            if status == ML600.HamiltonPumpIO.ACKNOWLEDGE:
                logger.debug("Positive acknowledge received")
            else:
                logger.warning("Negative acknowledge received")
                warnings.warn(
                    "Negative acknowledge reply received from pump: check command validity!"
                )

            return response[1:].rstrip()

        def reset_buffer(self):
            """Reset input buffer before reading from serial. In theory not necessary if all replies are consumed..."""
            self._serial.reset_input_buffer()

        async def write_and_read_reply_async(
            self, command: ML600.Protocol1Command
        ) -> str:
            """Send a command to the pump, read the replies and returns it, optionally parsed."""
            self.reset_buffer()
            await self._write_async(command.compile())
            response = await self._read_reply_async()

            if not response:
                raise InvalidConfiguration(
                    f"No response received from pump, check pump address! "
                    f"(Currently set to {command.target_pump_num})"
                )

            return self.parse_response(response)

        @property
        def name(self) -> str:
            """This is used to provide a nice-looking default name to pumps based on their serial connection."""
            try:
                return self._serial.name
            except AttributeError:
                return ""

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances: set[HamiltonPumpIO] = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy-chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).
    # FYI it is a borg idiom https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html

    class ValvePositionName(IntEnum):
        """Maps valve position to the corresponding number."""

        POSITION_1 = 1
        # POSITION_2 = 2
        POSITION_3 = 3
        INPUT = 9  # 9 is default inlet, i.e. 1
        OUTPUT = 10  # 10 is default outlet, i.e. 3
        WASH = 11  # 11 is default wash, i.e. undefined

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
        address: int = 1,
        name: str | None = None,
    ):
        """
        Default constructor, needs an HamiltonPumpIO object. See from_config() class method for config-based init.

        Args:
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump.
            syringe_volume: Volume of the syringe used, either a Quantity or number in ml.
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        super().__init__(name)
        # HamiltonPumpIO
        self.pump_io = pump_io
        ML600._io_instances.add(self.pump_io)  # See above for details.

        # Pump address is the pump sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # The pump name is used for logs and error messages.
        self.name = f"Pump {self.pump_io.name}:{address}" if name is None else name

        # Syringe pumps only perform linear movement, and the volume displaced is function of the syringe loaded.
        try:
            self.syringe_volume = ureg(syringe_volume)
        except AttributeError as attribute_error:
            raise InvalidConfiguration(
                f"{self.__class__.__name__}:{self.name} "
                f"Syringe volume must be a string parsable as pint.Quantity!\n"
                f"It is now a {type(syringe_volume)}: {syringe_volume} "
            ) from attribute_error

        if self.syringe_volume.m_as("ml") not in ML600.VALID_SYRINGE_VOLUME:
            raise InvalidConfiguration(
                f"The specified syringe volume ({syringe_volume}) does not seem to be valid!\n"
                f"The volume in ml has to be one of {ML600.VALID_SYRINGE_VOLUME}"
            )

        self._steps_per_ml = ureg(f"{48000 / self.syringe_volume} step/ml")
        self._offset_steps = 100  # Steps added to each absolute move command, to decrease wear and tear at volume = 0
        self._max_vol = (48000 - self._offset_steps) * ureg.step / self._steps_per_ml
        self._flow_rate = ureg("0.1 ml/min")
        self._withdraw_flow_rate = ureg("0.1 ml/min")

    @classmethod
    def from_config(cls, **config):
        """This class method is used to create instances via config file by the server for HTTP interface."""
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of HamiltonPumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        # HamiltonPump_IO() manually instantiated are not accounted for.
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
            pumpio = ML600.HamiltonPumpIO.from_config(config_for_pumpio)

        return cls(
            pumpio,
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name"),
        )

    async def initialize(self, hw_init=False, init_speed: str = "200 sec / stroke"):
        """Must be called after init before anything else."""
        if not self.pump_io._initialized:
            await self.pump_io.initialize()
        # Test connectivity by querying the pump's firmware version
        fw_cmd = ML600.Protocol1CommandTemplate(command="U").to_pump(self.address)
        firmware_version = await self.pump_io.write_and_read_reply_async(fw_cmd)
        logger.info(
            f"Connected to Hamilton ML600 {self.name} - FW version: {firmware_version}!"
        )

        if hw_init:
            await self.initialize_pump(speed=init_speed)

    async def send_command_and_read_reply(
        self,
        command_template: Protocol1CommandTemplate,
        command_value="",
        argument_value="",
    ) -> str:
        """Send a command based on its template by adding pump address and parameters, returns reply."""
        return await self.pump_io.write_and_read_reply_async(
            command_template.to_pump(self.address, command_value, argument_value)
        )

    def _validate_speed(self, speed_value: str | None) -> str:
        """
        Validate the speed.

        Given a speed (seconds/stroke) returns a valid value for it, and a warning if out of bounds.
        """
        # Validated speeds are used as command argument, with empty string being the default for None
        if speed_value is None:
            return ""

        speed = ureg(speed_value)

        # Alert if out of bounds but don't raise exceptions, according to general philosophy.
        # Target flow rate too high
        if speed < ureg("2 sec/stroke"):
            speed = ureg("2 sec/stroke")
            warnings.warn(
                f"Desired speed ({speed}) is unachievable!"
                f"Set to {self._seconds_per_stroke_to_flowrate(speed)}"
                f"Wrong units? A bigger syringe is needed?"
            )

        # Target flow rate too low
        if speed > ureg("3692 sec/stroke"):
            speed = ureg("3692 sec/stroke")
            warnings.warn(
                f"Desired speed ({speed}) is unachievable!"
                f"Set to {self._seconds_per_stroke_to_flowrate(speed)}"
                f"Wrong units? A smaller syringe is needed?"
            )

        return str(round(speed.m_as("sec / stroke")))

    async def initialize_pump(self, speed: str | None = None):
        """
        Initialize both syringe and valve.

        speed: 2-3692 in seconds/stroke
        """
        init_cmd = ML600.Protocol1CommandTemplate(command="X", optional_parameter="S")
        return await self.send_command_and_read_reply(
            init_cmd, argument_value=self._validate_speed(speed)
        )

    async def initialize_valve(self):
        """Initialize valve only."""
        return await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="LX")
        )

    async def initialize_syringe(self, speed: str | None = None):
        """
        Initialize syringe only.

        speed: 2-3692 in seconds/stroke
        """
        init_syringe_cmd = ML600.Protocol1CommandTemplate(
            command="X1", optional_parameter="S"
        )
        return await self.send_command_and_read_reply(
            init_syringe_cmd, argument_value=self._validate_speed(speed)
        )

    def flowrate_to_seconds_per_stroke(self, flowrate: str):
        """
        Convert flow rates to steps per seconds.

        To determine the volume dispensed per step the total syringe volume is divided by
        48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
        length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
        example to dispense 9 mL from a 10 mL syringe you would determine the number of
        steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
        """
        flowrate_w_units = ureg(flowrate)
        flowrate_in_steps_sec = flowrate_w_units * self._steps_per_ml
        seconds_per_stroke = (1 / flowrate_in_steps_sec).to("second/stroke")

        return self._validate_speed(str(seconds_per_stroke))

    def _seconds_per_stroke_to_flowrate(self, second_per_stroke) -> float:
        """Converts seconds per stroke to flow rate. Only internal use."""
        flowrate = 1 / (second_per_stroke * self._steps_per_ml)
        return flowrate.to("ml/min")

    def _volume_to_step_position(self, volume_w_units: str) -> int:
        """Convert a volume to a step position."""
        # noinspection PyArgumentEqualDefault
        volume = ureg(volume_w_units)
        steps = volume * self._steps_per_ml
        return round(steps.m_as("steps")) + self._offset_steps

    async def _to_step_position(self, position: int, speed: str = ""):
        """Absolute move to step position."""
        abs_move_cmd = ML600.Protocol1CommandTemplate(
            command="M", optional_parameter="S"
        )
        return await self.send_command_and_read_reply(
            abs_move_cmd, str(position), self._validate_speed(speed)
        )

    async def get_current_volume(self) -> str:
        """Return current syringe position in ml."""
        syringe_pos = await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="YQP")
        )
        current_steps = (int(syringe_pos) - self._offset_steps) * ureg.step
        return str(current_steps / self._steps_per_ml)

    async def to_volume(self, target_volume: str, speed: str = ""):
        """Absolute move to volume provided."""
        await self._to_step_position(
            self._volume_to_step_position(target_volume), speed
        )
        logger.debug(f"Pump {self.name} set to volume {target_volume} at speed {speed}")

    async def pause(self):
        """Pause any running command."""
        return await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="K", execute_command=False)
        )

    async def resume(self):
        """Resume any paused command."""
        return await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="$", execute_command=False)
        )

    async def set_flow_rate(self, rate: str):
        """Set pump infusion flow rate."""
        self._flow_rate = ureg(rate)

    async def get_flow_rate(self) -> float:
        """Get pump infusion flow rate."""
        return self._flow_rate.m_as("ml/min")

    async def set_withdrawing_flow_rate(self, rate: str):
        """Set pump withdraw flow rate."""
        self._withdraw_flow_rate = ureg(rate)

    async def get_withdrawing_flow_rate(self) -> float:
        """Get pump withdraw flow rate."""
        return self._withdraw_flow_rate.m_as("ml/min")

    async def infuse(self):
        """
        Start infusion.

        As default infuse current syringe volume to `output` position at pre-set flowrate.
        """
        self.deliver(
            volume=self.get_current_volume(),
            to_valve=ValvePositionName.OUTPUT,
            flowrate=str(self._flow_rate),
        )

    def withdraw(self):
        """Pump in the opposite direction of infuse."""
        self.deliver(
            volume=self._max_vol,
            to_valve=ValvePositionName.OUTPUT,
            flowrate=str(self._flow_rate),
        )

    async def stop(self):
        """Stop and abort any running command."""
        await self.pause()
        return await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="V", execute_command=False)
        )

    async def wait_until_idle(self):
        """Return when no more commands are present in the pump buffer."""
        logger.debug(f"ML600 pump {self.name} wait until idle...")
        while self.is_busy:
            time.sleep(0.1)
        logger.debug(f"...ML600 pump {self.name} idle now!")

    async def version(self) -> str:
        """Return the current firmware version reported by the pump."""
        return await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="U")
        )

    async def is_idle(self) -> bool:
        """Check if the pump is idle (actually check if the last command has ended)."""
        return (
            await self.send_command_and_read_reply(
                ML600.Protocol1CommandTemplate(command="F")
            )
            == "Y"
        )

    async def is_busy(self) -> bool:
        """Pump is not idle."""
        return not await self.is_idle()

    async def get_valve_position(self) -> ML600.ValvePositionName:
        """Represent the position of the valve: getter returns Enum, setter needs Enum."""
        valve_pos = await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="LQP")
        )
        return ML600.ValvePositionName(int(valve_pos))

    async def set_valve_position(
        self,
        target_position: ML600.ValvePositionName,
        wait_for_movement_end: bool = True,
    ):
        """Set valve position. wait_for_movement_end is defaulted to True as it is a common mistake not to wait..."""
        valve_by_name_cw = ML600.Protocol1CommandTemplate(command="LP0")
        valve_by_name_cw = ML600.Protocol1CommandTemplate(command="LP0")
        await self.send_command_and_read_reply(
            valve_by_name_cw, command_value=str(int(target_position))
        )
        logger.debug(f"{self.name} valve position set to {target_position.name}")
        if wait_for_movement_end:
            await self.wait_until_idle()

    async def get_return_steps(self) -> int:
        """Return steps' getter. Applied to the end of a downward syringe movement to removes mechanical slack."""
        steps = await self.send_command_and_read_reply(
            ML600.Protocol1CommandTemplate(command="YQN")
        )
        return int(steps)

    async def set_return_steps(self, target_steps: int):
        """Return steps' setter. Applied to the end of a downward syringe movement to removes mechanical slack."""
        set_return_steps_cmd = ML600.Protocol1CommandTemplate(command="YSN")
        await self.send_command_and_read_reply(
            set_return_steps_cmd, command_value=str(int(target_steps))
        )

    async def pickup(
        self,
        volume: str,
        from_valve: ML600.ValvePositionName,
        flowrate: str = "1 ml/min",
        wait: bool = False,
    ):
        """Get volume from valve specified at given flow rate."""
        cur_vol = ureg(await self.get_current_volume())
        if (cur_vol + volume) > self._max_vol:
            warnings.warn(
                f"Cannot withdraw {volume} given the current syringe position {cur_vol} and a "
                f"syringe volume of {self.syringe_volume}"
            )
            return

        # Valve to position specified
        await self.set_valve_position(from_valve)
        # Move up to target volume
        await self.to_volume(
            str(cur_vol + volume),
            speed=self.flowrate_to_seconds_per_stroke(flowrate),
        )

        if wait:
            await self.wait_until_idle()

    async def deliver(
        self,
        volume: str,
        to_valve: ML600.ValvePositionName,
        flowrate: str,
        wait: bool = False,
    ):
        """Deliver volume to valve specified at given flow rate."""
        cur_vol = ureg(await self.get_current_volume())
        if volume > cur_vol:
            warnings.warn(
                f"Cannot deliver {volume} given the current syringe position {cur_vol}!"
            )
            return

        # Valve to position specified
        await self.set_valve_position(to_valve)
        # Move up to target volume
        await self.to_volume(
            str(cur_vol - volume),
            speed=self.flowrate_to_seconds_per_stroke(flowrate),
        )

        if wait:
            await self.wait_until_idle()

    async def transfer(
        self,
        volume: str,
        from_valve: ML600.ValvePositionName,
        to_valve: ML600.ValvePositionName,
        flowrate_in: str = "1 ml/min",
        flowrate_out: str = "1 ml/min",
        wait: bool = False,
    ):
        """Move liquid from place to place."""
        await self.pickup(volume, from_valve, flowrate_in, wait=True)
        await self.deliver(volume, to_valve, flowrate_out, wait=wait)

    def get_components(self):
        """Return a Syringe and a Valve component."""
        # FIXME
        ...

        # From BasePump
        # router.add_api_route("/flow-rate", self.get_flow_rate, methods=["GET"])
        # router.add_api_route("/flow-rate", self.set_flow_rate, methods=["PUT"])
        # router.add_api_route("/infuse", self.infuse, methods=["PUT"])
        # router.add_api_route("/stop", self.stop, methods=["PUT"])

        # router.add_api_route("/firmware-version", self.version, methods=["GET"])
        # router.add_api_route("/initialize/pump", self.initialize_pump, methods=["PUT"])
        # router.add_api_route(
        #     "/initialize/valve", self.initialize_valve, methods=["PUT"]
        # )
        # router.add_api_route(
        #     "/initialize/syringe", self.initialize_syringe, methods=["PUT"]
        # )
        # router.add_api_route("/pause", self.pause, methods=["PUT"])
        # router.add_api_route("/resume", self.resume, methods=["PUT"])
        # router.add_api_route("/is-idle", self.is_idle, methods=["GET"])
        # router.add_api_route("/is-busy", self.is_busy, methods=["GET"])
        # router.add_api_route(
        #     "/valve/position", self.get_valve_position, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/valve/position", self.set_valve_position, methods=["PUT"]
        # )
        # router.add_api_route(
        #     "/syringe/volume", self.get_current_volume, methods=["GET"]
        # )
        # router.add_api_route("/syringe/volume", self.to_volume, methods=["PUT"])
        # router.add_api_route(
        #     "/syringe/return-steps", self.get_return_steps, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/syringe/return-steps", self.set_return_steps, methods=["PUT"]
        # )
        # router.add_api_route("/pickup", self.pickup, methods=["PUT"])
        # router.add_api_route("/deliver", self.deliver, methods=["PUT"])
        # router.add_api_route(
        #     "/transfer", self.transfer, methods=["PUT"]
        # )  # Might go in timeout
        #
        # return router


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
