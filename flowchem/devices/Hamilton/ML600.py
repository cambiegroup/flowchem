"""
This module is used to control Hamilton ML600 syringe pump via the protocol1/RNO+.
"""

from __future__ import annotations

import logging
import string
import threading
import time
import warnings
from dataclasses import dataclass
from enum import IntEnum
from threading import Thread
from typing import Optional

import aioserial
from aioserial import SerialException

from flowchem.exceptions import InvalidConfiguration


@dataclass
class Protocol1CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """

    command: str
    optional_parameter: str = ""
    execute_command: bool = True

    def to_pump(
        self, address: int, command_value: str = "", argument_value: str = ""
    ) -> Protocol1Command:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        return Protocol1Command(
            target_pump_num=address,
            command=self.command,
            optional_parameter=self.optional_parameter,
            command_value=command_value,
            argument_value=argument_value,
            execute_command=self.execute_command,
        )


@dataclass
class Protocol1Command(Protocol1CommandTemplate):
    """ Class representing a pump command and its expected reply """

    PUMP_ADDRESS = {
        pump_num: address
        for (pump_num, address) in enumerate(string.ascii_lowercase[:16], start=1)
    }
    # i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}
    # Note ':' is used for broadcast within the daisy chain.

    target_pump_num: Optional[int] = 1
    command_value: Optional[str] = None
    argument_value: Optional[str] = None

    def compile(self) -> bytes:
        """ Create actual command byte by prepending pump address to command and appending executing command. """
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
    """ Setup with serial parameters, low level IO"""

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
        Initialize communication on the serial port where the pumps are located and initialize them
        Args:
            aio_port: aioserial.Serial() object
        """

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self._serial = aio_port

        # These will be set by `HamiltonPumpIO.initialize()`
        self._initialized = False
        self.num_pump_connected = False

    @classmethod
    def from_config(cls, config):
        """ Create HamiltonPumpIO from config. """
        # Merge default settings, including serial, with provided ones.
        configuration = dict(HamiltonPumpIO.DEFAULT_CONFIG, **config)

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except SerialException as e:
            raise InvalidConfiguration(
                f"Cannot connect to the pump on the port <{configuration.get('port')}>"
            ) from e

        return cls(serial_object)

    async def initialize(self, hw_initialization: bool = True):
        """
        Ensure connection with pump + initialize

        Args:
            hw_initialization: Whether each pumps has to be initialized. Note that this might be undesired!
        """
        # This has to be run after each power cycle to assign addresses to pumps
        self.num_pump_connected = self._assign_pump_address()
        if hw_initialization:
            await self._hw_init()

    async def _assign_pump_address(self) -> int:
        """
        To be run on init, auto assign addresses to pumps based on their position on the daisy chain!
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        try:
            await self._write_async("1a\r".encode("ascii"))
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

        reply = await self._read_reply_async()
        if reply and reply[:1] == "1":
            # reply[1:2] should be the address of the last pump. However, this does not work reliably.
            # So here we enumerate the pumps explicitly instead
            last_pump = 0
            for pump_num, address in Protocol1Command.PUMP_ADDRESS.items():
                await self._write_async(f"{address}UR\r".encode("ascii"))
                if "NV01" in await self._read_reply_async():
                    last_pump = pump_num
                else:
                    break
            self.logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
            return int(last_pump)
        else:
            raise InvalidConfiguration(f"No pump found on {self._serial.port}")

    async def _hw_init(self):
        """ Send to all pumps the HW initialization command (i.e. homing) """
        await self._write_async(b":XR\r")  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

    async def _write_async(self, command: bytes):
        """ Writes a command to the pump """
        await self._serial.write_async(command)
        self.logger.debug(f"Command {repr(command)} sent!")

    async def _read_reply_async(self) -> str:
        """ Reads the pump reply from serial communication """
        reply_string = await self._serial.readline_async()
        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string.decode("ascii")

    def parse_response(self, response: str) -> str:
        """ Split a received line in its components: success, reply """
        status = response[:1]
        assert status in (
            HamiltonPumpIO.ACKNOWLEDGE,
            HamiltonPumpIO.NEGATIVE_ACKNOWLEDGE,
        ), "Invalid status reply!"

        if status == HamiltonPumpIO.ACKNOWLEDGE:
            self.logger.debug("Positive acknowledge received")
        else:
            self.logger.warning("Negative acknowledge received")
            warnings.warn(
                "Negative acknowledge reply received from pump: check command validity!"
            )

        return response[1:].rstrip()

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        self._serial.reset_input_buffer()

    async def write_and_read_reply_async(self, command: Protocol1Command) -> str:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
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
        """ This is used to provide a nice-looking default name to pumps based on their serial connection. """
        try:
            return self._serial.name
        except AttributeError:
            return ""


class ML600:
    """" ML600 implementation according to docs. Tested on 61501-01 (single syringe).

    From docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).
    # FYI it is a borg idiom https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html

    class ValvePositionName(IntEnum):
        """ Maps valve position to the corresponding number """

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
        syringe_volume: float,
        address: int = 1,
        name: str = None,
    ):
        """
        Default constructor, needs an HamiltonPumpIO object. See from_config() class method for config-based init.

        Args:
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump.
            syringe_volume: Volume of the syringe used, in ml.
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        # HamiltonPumpIO
        self.pump_io = pump_io
        ML600._io_instances.add(self.pump_io)  # See above for details.

        # Pump address is the pump sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # The pump name is used for logs and error messages.
        self.name = f"Pump {self.pump_io.name}:{address}" if name is None else name

        # Syringe pumps only perform linear movement, and the volume displaced is function of the syringe loaded.
        if syringe_volume not in ML600.VALID_SYRINGE_VOLUME:
            raise InvalidConfiguration(
                f"The specified syringe volume ({syringe_volume}) does not seem to be valid!\n"
                f"The volume in ml has to be one of {ML600.VALID_SYRINGE_VOLUME}"
            )
        self.syringe_volume = syringe_volume
        self._steps_per_ml = 48000 / self.syringe_volume
        self._offset_steps = 100  # Steps added to each absolute move command, to decrease wear and tear at volume = 0
        self._max_vol = (48000 - self._offset_steps) / self._steps_per_ml

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

    @classmethod
    def from_config(cls, config):
        """ This class method is used to create instances via config file by the server for HTTP interface. """
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
            pumpio = HamiltonPumpIO.from_config(config_for_pumpio)

        return cls(
            pumpio,
            syringe_volume=config.get("syringe_volume"),
            address=config.get("address"),
            name=config.get("name"),
        )

    async def initialize(self):
        """ Needs to be called after init before anything else. """
        # Test connectivity by querying the pump's firmware version
        fw_cmd = Protocol1CommandTemplate(command="U").to_pump(self.address)
        firmware_version = await self.pump_io.write_and_read_reply_async(fw_cmd)
        self.log.info(f"Connected to Hamilton ML600 {self.name} - FW version: {firmware_version}!")

    async def send_command_and_read_reply(
        self,
        command_template: Protocol1CommandTemplate,
        command_value="",
        argument_value="",
    ) -> str:
        """ Sends a command based on its template by adding pump address and parameters, returns reply """
        return await self.pump_io.write_and_read_reply_async(
            command_template.to_pump(self.address, command_value, argument_value)
        )

    @staticmethod
    def _validate_speed(speed: int = None) -> str:
        """ Given a arbitrary speed (seconds/stroke) returns a valid command value for it. """
        if speed is None:
            return ""
        # Cast to int
        speed = int(round(speed))
        if not 2 <= speed <= 3692:
            warnings.warn(
                "Invalid initialization speed provided: {speed}. Acceptable range is 2-3692! Ignoring value."
            )
            return ""
        return str(speed)

    async def initialize_pump(self, speed: int = None):
        """
        Initialize both syringe and valve
        speed: 2-3692 is in seconds/stroke
        """
        init_cmd = Protocol1CommandTemplate(command="X", optional_parameter="S")
        return await self.send_command_and_read_reply(
            init_cmd, argument_value=self._validate_speed(speed)
        )

    async def initialize_valve(self):
        """ Initialize valve only """
        return await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="LX")
        )

    async def initialize_syringe(self, speed: int = None):
        """
        Initialize syringe only
        speed: 2-3692 is in seconds/stroke
        """
        init_syringe_cmd = Protocol1CommandTemplate(
            command="X1", optional_parameter="S"
        )
        return await self.send_command_and_read_reply(
            init_syringe_cmd, argument_value=self._validate_speed(speed)
        )

    def flowrate_to_seconds_per_stroke(self, flowrate_in_ml_min: float):
        """
        Convert flow rates in ml/min to steps per seconds

        To determine the volume dispensed per step the total syringe volume is divided by
        48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
        length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
        example to dispense 9 mL from a 10 mL syringe you would determine the number of
        steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
        """
        flowrate_in_ml_sec = flowrate_in_ml_min / 60
        flowrate_in_steps_sec = flowrate_in_ml_sec * self._steps_per_ml
        seconds_per_stroke = round(48000 / flowrate_in_steps_sec)

        # Alert if out of bounds but don't raise exceptions, according to general philosophy.
        # Target flow rate too high
        if seconds_per_stroke < 2:
            seconds_per_stroke = 2
            warnings.warn(
                f"Desired flow rate ({flowrate_in_ml_min}) is unachievable!"
                f"Set to {self.seconds_per_stroke_to_flowrate(seconds_per_stroke)}"
                f"Wrong units? A bigger syringe is needed?"
            )

        # Target flow rate too low
        if seconds_per_stroke > 3692:
            seconds_per_stroke = 3692
            warnings.warn(
                f"Desired flow rate ({flowrate_in_ml_min}) is unachievable!"
                f"Set to {self.seconds_per_stroke_to_flowrate(seconds_per_stroke)}"
                f"Wrong units? A smaller syringe is needed?"
            )

        return round(seconds_per_stroke)

    def seconds_per_stroke_to_flowrate(self, seconds_per_stroke: int) -> float:
        """ The inverse of flowrate_to_seconds_per_stroke(). """
        flowrate_in_steps_second = seconds_per_stroke * 48000
        flowrate_in_ml_sec = flowrate_in_steps_second / self._steps_per_ml
        flowrate_in_ml_min = flowrate_in_ml_sec * 60
        return flowrate_in_ml_min

    def _volume_to_step(self, volume_in_ml: float) -> int:
        """ Converts a volume to a step position. """
        return round(volume_in_ml * self._steps_per_ml) + self._offset_steps

    async def _to_step_position(self, position: int, speed: int = ""):
        """ Absolute move to step position. """
        abs_move_cmd = Protocol1CommandTemplate(command="M", optional_parameter="S")
        return await self.send_command_and_read_reply(
            abs_move_cmd, str(position), self._validate_speed(speed)
        )

    async def get_current_volume(self) -> float:
        """ Return current syringe position in ml. """
        syringe_pos = await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="YQP")
        )
        current_steps = int(syringe_pos) - self._offset_steps
        return current_steps / self._steps_per_ml

    async def to_volume(self, volume_in_ml: float, speed: int = ""):
        """ Absolute move to volume provided. """
        await self._to_step_position(self._volume_to_step(volume_in_ml), speed)
        self.log.debug(
            f"Pump {self.name} set to volume {volume_in_ml} at speed {speed}"
        )

    async def pause(self):
        """ Pause any running command. """
        return await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="K", execute_command=False)
        )

    async def resume(self):
        """ Resume any paused command. """
        return await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="$", execute_command=False)
        )

    async def stop(self):
        """ Stops and abort any running command. """
        await self.pause()
        return await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="V", execute_command=False)
        )

    async def wait_until_idle(self):
        """ Returns when no more commands are present in the pump buffer. """
        self.log.debug(f"ML600 pump {self.name} wait until idle...")
        while self.is_busy:
            time.sleep(0.1)
        self.log.debug(f"...ML600 pump {self.name} idle now!")

    async def version(self) -> str:
        """ Returns the current firmware version reported by the pump. """
        return await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="U")
        )

    async def is_idle(self) -> bool:
        """ Checks if the pump is idle (actually check if the last command has ended). """
        return (
            await self.send_command_and_read_reply(
                Protocol1CommandTemplate(command="F")
            )
            == "Y"
        )

    async def is_busy(self) -> bool:
        """ Pump is not idle. """
        return not await self.is_idle()

    async def get_valve_position(self) -> ValvePositionName:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum. """
        valve_pos = await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="LQP")
        )
        return ML600.ValvePositionName(int(valve_pos))

    async def set_valve_position(
        self, target_position: ValvePositionName, wait_for_movement_end: bool = True
    ):
        """ Set valve position. wait_for_movement_end is defaulted to True as it is a common mistake not to wait... """
        valve_by_name_cw = Protocol1CommandTemplate(command="LP0")
        await self.send_command_and_read_reply(
            valve_by_name_cw, command_value=str(int(target_position))
        )
        self.log.debug(f"{self.name} valve position set to {target_position.name}")
        if wait_for_movement_end:
            await self.wait_until_idle()

    async def get_return_steps(self) -> int:
        """ Return steps getter. Applied to the end of a downward syringe movement to removes mechanical slack. """
        steps = await self.send_command_and_read_reply(
            Protocol1CommandTemplate(command="YQN")
        )
        return int(steps)

    async def set_return_steps(self, target_steps: int):
        """ Return steps setter. Applied to the end of a downward syringe movement to removes mechanical slack. """
        set_return_steps_cmd = Protocol1CommandTemplate(command="YSN")
        await self.send_command_and_read_reply(
            set_return_steps_cmd, command_value=str(int(target_steps))
        )

    async def pickup(
        self,
        volume_in_ml: float,
        from_valve: ValvePositionName,
        flowrate_in_ml_min: float = 1.0,
        wait: bool = False,
    ):
        """ Get volume from valve specified at given flowrate. """
        cur_vol = await self.get_current_volume()
        if (cur_vol + volume_in_ml) > self._max_vol:
            warnings.warn(
                f"Cannot withdraw {volume_in_ml} given the current syringe position {cur_vol} ml and a "
                f"syringe volume of {self.syringe_volume}"
            )
            return

        # Valve to position specified
        await self.set_valve_position(from_valve, wait_for_movement_end=True)
        # Move up to target volume
        await self.to_volume(
            cur_vol + volume_in_ml,
            speed=self.flowrate_to_seconds_per_stroke(flowrate_in_ml_min),
        )

        if wait:
            await self.wait_until_idle()

    async def deliver(
        self,
        volume_in_ml: float,
        to_valve: ValvePositionName,
        flowrate_in_ml_min: float = 1.0,
        wait: bool = False,
    ):
        """ Delivers volume to valve specified at given flowrate. """
        cur_vol = await self.get_current_volume()
        if volume_in_ml > cur_vol:
            warnings.warn(
                f"Cannot deliver {volume_in_ml} given the current syringe position {cur_vol} ml!"
            )
            return

        # Valve to position specified
        await self.set_valve_position(to_valve, wait_for_movement_end=True)
        # Move up to target volume
        await self.to_volume(
            cur_vol - volume_in_ml,
            speed=self.flowrate_to_seconds_per_stroke(flowrate_in_ml_min),
        )

        if wait:
            await self.wait_until_idle()

    async def transfer(
        self,
        volume_in_ml: float,
        from_valve: ValvePositionName,
        to_valve: ValvePositionName,
        flowrate_in: float = 1.0,
        flowrate_out: float = 1.0,
        wait: bool = False,
    ):
        """ Move liquid from place to place. """
        await self.pickup(volume_in_ml, from_valve, flowrate_in, wait=True)
        await self.deliver(volume_in_ml, to_valve, flowrate_out, wait=wait)

    def get_router(self):
        """ Creates an APIRouter for this object. """
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/firmware-version", self.version, methods=["GET"])
        router.add_api_route("/initialize/pump", self.initialize_pump, methods=["PUT"])
        router.add_api_route(
            "/initialize/valve", self.initialize_valve, methods=["PUT"]
        )
        router.add_api_route(
            "/initialize/syringe", self.initialize_syringe, methods=["PUT"]
        )
        router.add_api_route("/pause", self.pause, methods=["PUT"])
        router.add_api_route("/resume", self.resume, methods=["PUT"])
        router.add_api_route("/resume", self.resume, methods=["PUT"])
        router.add_api_route("/stop", self.stop, methods=["PUT"])
        router.add_api_route("/version", self.stop, methods=["PUT"])
        router.add_api_route("/is-idle", self.is_idle, methods=["GET"])
        router.add_api_route("/is-busy", self.is_busy, methods=["GET"])
        router.add_api_route(
            "/valve/position", self.get_valve_position, methods=["GET"]
        )
        router.add_api_route(
            "/valve/position", self.set_valve_position, methods=["PUT"]
        )
        router.add_api_route(
            "/syringe/volume", self.get_current_volume, methods=["GET"]
        )
        router.add_api_route("/syringe/volume", self.to_volume, methods=["PUT"])
        router.add_api_route(
            "/syringe/return-steps", self.get_return_steps, methods=["GET"]
        )
        router.add_api_route(
            "/syringe/return-steps", self.set_return_steps, methods=["PUT"]
        )
        router.add_api_route("/pickup", self.pickup, methods=["PUT"])
        router.add_api_route("/deliver", self.deliver, methods=["PUT"])
        # router.add_api_route("/transfer", self.transfer, methods=["PUT"])  # Might go in timeout

        return router


class TwoPumpAssembly(Thread):
    """
    Thread to control two pumps and have them generating a continuous flow.
    Note that the pumps should not be accessed directly when used in a TwoPumpAssembly!

    Notes: this needs to start a thread owned by the instance to control the pumps.
    The async version of this being possibly simpler w/ tasks and callback :)
    """

    def __init__(
        self, pump1: ML600, pump2: ML600, target_flowrate: float, init_seconds: int = 10
    ):
        super(TwoPumpAssembly, self).__init__()
        self._p1 = pump1
        self._p2 = pump2
        self.daemon = True
        self.cancelled = threading.Event()
        self._flowrate = target_flowrate
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        # How many seconds per stroke for first filling? application dependent, as fast as possible, but not too much.
        self.init_secs = init_seconds

        # While in principle possible, using syringes of different volumes is discouraged, hence...
        assert (
            pump1.syringe_volume == pump2.syringe_volume
        ), "Syringes w/ equal volume are needed for continuous flow!"
        # self._p1.initialize_pump()
        # self._p2.initialize_pump()

    @property
    def flowrate(self):
        """ Returns/sets flowrate. """
        return self._flowrate

    @flowrate.setter
    def flowrate(self, target_flowrate):
        if target_flowrate == 0:
            warnings.warn(
                "Cannot set flowrate to 0! Pump stopped instead, restart previous flowrate with resume!"
            )
            self.cancel()
        else:
            self._flowrate = target_flowrate

        # This will stop current movement, make wait_for_both_pumps() return and move on w/ updated speed
        self._p1.stop()
        self._p2.stop()

    def wait_for_both_pumps(self):
        """ Custom waiting method to wait a shorter time than normal (for better sync) """
        while self._p1.is_busy or self._p2.is_busy:
            time.sleep(0.01)  # 10ms sounds reasonable to me
        self.log.debug("Pumps ready!")

    def _speed(self):
        speed = self._p1.flowrate_to_seconds_per_stroke(self._flowrate)
        self.log.debug(f"Speed calculated as {speed}")
        return speed

    def execute_stroke(
        self, pump_full: ML600, pump_empty: ML600, speed_s_per_stroke: int
    ):
        """ Perform a cycle (1 syringe stroke) in the continuous-operation mode. See also run(). """
        # Logic is a bit complex here to ensure pause-less pumping
        # This needs the pump that withdraws to move faster than the pumping one. no way around.

        # First start pumping with the full syringe already prepared
        pump_full.to_volume(0, speed=speed_s_per_stroke)
        self.log.debug("Pumping...")
        # Then start refilling the empty one
        pump_empty.valve_position = pump_empty.ValvePositionName.INPUT
        # And do that fast so that we finish refill before the pumping is over
        pump_empty.to_volume(pump_empty.syringe_volume, speed=speed_s_per_stroke - 5)
        pump_empty.wait_until_idle()
        # This allows us to set the right pump position on the pump that was empty (not full and ready for next cycle)
        pump_empty.valve_position = pump_empty.ValvePositionName.OUTPUT
        pump_full.wait_until_idle()

    def run(self):
        """Overloaded Thread.run, runs the update
        method once per every 10 milliseconds."""
        # First initialize with init_secs speed...
        self._p1.to_volume(self._p1.syringe_volume, speed=self.init_secs)
        self._p1.wait_until_idle()
        self._p1.valve_position = self._p1.ValvePositionName.OUTPUT
        self.log.info("Pumps initialized for continuous pumping!")

        while True:
            while not self.cancelled.is_set():
                self.execute_stroke(
                    self._p1, self._p2, speed_s_per_stroke=self._speed()
                )
                self.execute_stroke(
                    self._p2, self._p1, speed_s_per_stroke=self._speed()
                )

    def cancel(self):
        """ Cancel continuous-pumping assembly """
        self.cancelled.set()
        self._p1.stop()
        self._p2.stop()

    def resume(self):
        """ Resume continuous-pumping assembly """
        self.cancelled.clear()

    def stop_and_return_solution_to_container(self):
        """ Let´s not waste our precious stock solutions ;) """
        self.cancel()
        self.log.info(
            "Returning the solution currently loaded in the syringes back to the inlet.\n"
            "Make sure the container is not removed yet!"
        )
        # Valve to input
        self._p1.valve_position = self._p1.ValvePositionName.INPUT
        self._p2.valve_position = self._p2.ValvePositionName.INPUT
        self.wait_for_both_pumps()
        # Volume to 0 with the init speed (supposedly safe for this application)
        self._p1.to_volume(0, speed=self.init_secs)
        self._p2.to_volume(0, speed=self.init_secs)
        self.wait_for_both_pumps()
        self.log.info("Pump flushing completed!")


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM12",
        "address": 1,
        "name": "test1",
        "syringe_volume": 5,
    }
    pump1 = ML600.from_config(conf)
    asyncio.run(pump1.initialize_pump())
