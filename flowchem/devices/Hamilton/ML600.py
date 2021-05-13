"""
This module is used to control Hamilton ML600 syringe pump via the protocol1/RNO+.
"""

from __future__ import annotations

import io
import string
import time
import warnings

import serial
import logging
import threading
from enum import IntEnum
from dataclasses import dataclass
from typing import Union, List, Tuple, Optional
from serial import PARITY_EVEN, SEVENBITS, STOPBITS_ONE
from threading import Thread


class ML600Exception(Exception):
    """ General pump exception """
    pass


class InvalidConfiguration(ML600Exception):
    """ Used for failure in the serial communication """
    pass


class InvalidArgument(ML600Exception):
    """ A valid command was followed by an invalid command_value, usually out of accepted range """
    pass


@dataclass
class Protocol1CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """
    command: str
    optional_parameter: str = ""
    execute_command: bool = True

    def to_pump(self, address: int, command_value: str = '',  argument_value: str = '') -> Protocol1Command:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        return Protocol1Command(target_pump_num=address, command=self.command,
                                optional_parameter=self.optional_parameter, command_value=command_value,
                                argument_value=argument_value, execute_command=self.execute_command)


@dataclass
class Protocol1Command(Protocol1CommandTemplate):
    """ Class representing a pump command and its expected reply """
    # TODO move these two vars elsewhere!
    # ':' is used for broadcast within the daisy chain.
    PUMP_ADDRESS = {pump_num: address for (pump_num, address) in enumerate(string.ascii_lowercase[:16], start=1)}
    REVERSED_PUMP_ADDRESS = {value: key for (key, value) in PUMP_ADDRESS.items()}
    # i.e. PUMP_ADDRESS = {1:"a", 2:"b"... }

    target_pump_num: Optional[int] = 1
    command_value: Optional[str] = None
    argument_value: Optional[str] = None

    def compile(self) -> str:
        """
        Create actual command byte by prepending pump address to command and appending executing command.
        """
        assert self.target_pump_num in range(1, 17)

        compiled_command = f"{self.PUMP_ADDRESS[self.target_pump_num]}" \
                           f"{self.command}{self.command_value}"

        if self.argument_value:
            compiled_command += f"{self.optional_parameter}{self.argument_value}"\

        # Add execution flag at the end
        if self.execute_command is True:
            compiled_command += "R"

        return compiled_command + "\r"


class HamiltonPumpIO:
    """ Setup with serial parameters, low level IO"""
    ACKNOWLEDGE = chr(6)
    NEGATIVE_ACKNOWLEDGE = chr(21)

    def __init__(self, port: Union[int, str], baud_rate: int = 9600, hw_initialization: bool = True):
        """
        Initialize communication on the serial port where the pumps are located and initialize them
        Args:
            port: Serial port identifier
            baud_rate: Well, the baud rate :D
            hw_initialization: Whether each pumps has to be initialized. Note that this might be undesired!
        """
        if baud_rate not in serial.serialutil.SerialBase.BAUDRATES:
            raise InvalidConfiguration(f"Invalid baud rate provided {baud_rate}!")

        if isinstance(port, int):
            port = f"COM{port}"

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.lock = threading.Lock()

        try:
            # noinspection PyPep8
            self._serial = serial.Serial(port=port, baudrate=baud_rate, parity=PARITY_EVEN,
                                         stopbits=STOPBITS_ONE, bytesize=SEVENBITS,
                                         timeout=0.1)  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration(f"Check serial port availability! [{port}]") from e

        self.sio = io.TextIOWrapper(buffer=io.BufferedRWPair(self._serial, self._serial), line_buffering=True,
                                    newline="\r")

        # This has to be run after each power cycle to assign addresses to pumps
        self._assign_pump_address()
        if hw_initialization:
            self._hw_init()

    def _assign_pump_address(self):
        """
        To be run on init, auto assign addresses to pumps based on their position on the daisy chain!
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        self._write("1a\r")
        reply = self._read_reply()
        if reply and reply[:1] == "1":
            last_pump = Protocol1Command.REVERSED_PUMP_ADDRESS[reply[1:2]]
            self.logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
            return last_pump
        else:
            raise InvalidConfiguration(f"No pump available on {self._serial.port}")

    def _hw_init(self):
        """ Send to all pumps the HW initialization command (i.e. homing) """
        self._write(":XR\r")  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

    def _write(self, command: str):
        """ Writes a command to the pump """
        self.logger.debug(f"Sending {repr(command)}")
        try:
            self.sio.write(command)
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration from e

    def _read_reply(self) -> str:
        """ Reads the pump reply from serial communication """
        reply_string = self.sio.readline()
        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def parse_response(self, response: str) -> Tuple[bool, str]:
        """ Split a received line in its components: success, reply """
        if response[:1] == HamiltonPumpIO.ACKNOWLEDGE:
            self.logger.debug("Positive acknowledge received")
            success = True
        elif response[:1] == HamiltonPumpIO.NEGATIVE_ACKNOWLEDGE:
            self.logger.debug("Negative acknowledge received")
            success = False
        else:
            raise ML600Exception(f"This should not happen. Invalid reply: {response}!")

        return success, response[1:].rstrip()

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        try:
            self._serial.reset_input_buffer()
        except serial.PortNotOpenError as e:
            raise InvalidConfiguration from e

    def write_and_read_reply(self, command: Protocol1Command) -> str:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        with self.lock:
            self.reset_buffer()
            self._write(command.compile())
            response = self._read_reply()

        if not response:
            raise InvalidConfiguration(f"No response received from pump, check pump address! "
                                       f"(Currently set to {command.target_pump_num})")

        # Parse reply
        success, parsed_response = self.parse_response(response)

        assert success is True  # :)
        return parsed_response

    @property
    def name(self) -> Optional[str]:
        """ This is used to provide a nice-looking default name to pumps based on their serial connection. """
        try:
            return self._serial.name
        except AttributeError:
            return None


class ML600Commands:
    """ Just a collection of commands. Grouped here to ease future, unlikely, changes. """
    PAUSE = Protocol1CommandTemplate(command="K", execute_command=False)
    RESUME = Protocol1CommandTemplate(command="$", execute_command=False)
    CLEAR_BUFFER = Protocol1CommandTemplate(command="V", execute_command=False)

    STATUS = Protocol1CommandTemplate(command="U")
    INIT_ALL = Protocol1CommandTemplate(command="X", optional_parameter="S")
    INIT_VALVE_ONLY = Protocol1CommandTemplate(command="LX")
    INIT_SYRINGE_ONLY = Protocol1CommandTemplate(command="X1", optional_parameter="S")

    # SYRINGE POSITION
    PICKUP = Protocol1CommandTemplate(command="P", optional_parameter="S")
    DELIVER = Protocol1CommandTemplate(command="D", optional_parameter="S")
    ABSOLUTE_MOVE = Protocol1CommandTemplate(command="M", optional_parameter="S")

    # VALVE POSITION
    VALVE_TO_INLET = Protocol1CommandTemplate(command="I")
    VALVE_TO_OUTLET = Protocol1CommandTemplate(command="O")
    VALVE_TO_WASH = Protocol1CommandTemplate(command="W")
    VALVE_BY_NAME_CW = Protocol1CommandTemplate(command="LP0")
    VALVE_BY_NAME_CCW = Protocol1CommandTemplate(command="LP1")
    VALVE_BY_ANGLE_CW = Protocol1CommandTemplate(command="LA0")
    VALVE_BY_ANGLE_CCW = Protocol1CommandTemplate(command="LA1")

    # STATUS REQUEST
    # INFORMATION REQUEST -- these all returns Y/N/* where * means busy
    REQUEST_DONE = Protocol1CommandTemplate(command="F")
    SYRINGE_HAS_ERROR = Protocol1CommandTemplate(command="Z")
    VALVE_HAS_ERROR = Protocol1CommandTemplate(command="G")
    IS_SINGLE_SYRINGE = Protocol1CommandTemplate(command="H")
    # STATUS REQUEST  - these have complex responses, see relevant methods for details.
    STATUS_REQUEST = Protocol1CommandTemplate(command="E1")
    ERROR_REQUEST = Protocol1CommandTemplate(command="E2")
    TIMER_REQUEST = Protocol1CommandTemplate(command="E3")
    BUSY_STATUS = Protocol1CommandTemplate(command="T1")
    ERROR_STATUS = Protocol1CommandTemplate(command="T2")
    # PARAMETER REQUEST
    SYRINGE_DEFAULT_SPEED = Protocol1CommandTemplate(command="YQS")  # 2-3692 seconds per stroke
    SYRINGE_DEFAULT_RETURN = Protocol1CommandTemplate(command="YQN")  # 0-1000 steps
    CURRENT_SYRINGE_POSITION = Protocol1CommandTemplate(command="YQP")  # 0-52800 steps
    SYRINGE_DEFAULT_BACKOFF = Protocol1CommandTemplate(command="YQP")  # 0-1000 steps
    CURRENT_VALVE_POSITION = Protocol1CommandTemplate(command="LQP")  # 1-8 (see docs, Table 3.2.2)
    # VALVE REQUEST
    VALVE_ANGLE = Protocol1CommandTemplate(command="LQA")  # 0-359 degrees
    VALVE_CONFIGURATION = Protocol1CommandTemplate(command="YQS")  # 11-20 (see docs, Table 3.2.2)
    VALVE_SPEED = Protocol1CommandTemplate(command="LQF")  # 15-720 degrees per sec
    # TIMER REQUEST
    TIMER_DELAY = Protocol1CommandTemplate(command="<T")  # 0–99999999 ms
    # FIRMWARE REQUEST
    FIRMWARE_VERSION = Protocol1CommandTemplate(command="U")  # xxii.jj.k (ii major, jj minor, k revision)


class ML600:
    """" ML600 implementation according to docs. Tested on 61501-01 (single syringe).

    From docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """
    class ValvePositionName(IntEnum):
        """ Maps valve position to the corresponding number """
        POSITION_1 = 1
        # POSITION_2 = 2
        POSITION_3 = 3
        INPUT = 9  # 9 is default inlet, i.e. 1
        OUTPUT = 10  # 10 is default outlet, i.e. 3
        WASH = 11  # 11 is default wash, i.e. undefined

    VALID_SYRINGE_VOLUME = {0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0}

    def __init__(self, pump_io: HamiltonPumpIO, syringe_volume: float, address: int = 1, name: str = None):
        """

        Args:
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump
            syringe_volume: Volume of the syringe used, in ml
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important
        """
        self.pump_io = pump_io
        self.name = f"Pump {self.pump_io.name}:{address}" if name is None else name
        self.address: int = address
        if syringe_volume not in ML600.VALID_SYRINGE_VOLUME:
            raise InvalidConfiguration(f"The specified syringe volume ({syringe_volume}) does not seem to be valid!\n"
                                       f"The volume in ml has to be one of {ML600.VALID_SYRINGE_VOLUME}")
        self.syringe_volume = syringe_volume
        self.steps_per_ml = 48000 / self.syringe_volume
        self.offset_steps = 100  # Steps added to each absolute move command, to decrease wear and tear at volume = 0

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by HamiltonPumpIO
        self.log.info(f"Connected to pump '{self.name}'  FW version: {self.firmware_version}!")

    def send_command_and_read_reply(self, command_template: Protocol1CommandTemplate, command_value='',
                                    argument_value='') -> str:
        """ Sends a command based on its template and return the corresponding reply as str """
        return self.pump_io.write_and_read_reply(command_template.to_pump(self.address, command_value, argument_value))

    def initialize_pump(self, speed: int = None):
        """
        Initialize both syringe and valve
        speed: 2-3692 is in seconds/stroke
        """
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL, argument_value=str(speed))
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL)

    def initialize_valve(self):
        """
        Initialize valve only
        """
        return self.send_command_and_read_reply(ML600Commands.INIT_VALVE_ONLY)

    def initialize_syringe(self, speed: int = None):
        """
        Initialize syringe only
        speed: 2-3692 is in seconds/stroke
        """
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(ML600Commands.INIT_SYRINGE_ONLY, argument_value=str(speed))
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_SYRINGE_ONLY)

    def flowrate_to_seconds_per_stroke(self, flowrate_in_ml_min: float):
        """
        Convert flow rates in ml/min to steps per seconds

        To determine the volume dispensed per step the total syringe volume is divided by
        48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
        length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
        example to dispense 9 mL from a 10 mL syringe you would determine the number of
        steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
        """
        assert flowrate_in_ml_min > 0
        flowrate_in_ml_sec = flowrate_in_ml_min / 60
        flowrate_in_steps_sec = flowrate_in_ml_sec * self.steps_per_ml
        seconds_per_stroke = round(48000 / flowrate_in_steps_sec)
        assert 2 <= seconds_per_stroke <= 3692
        return round(seconds_per_stroke)

    def _volume_to_step(self, volume_in_ml: float) -> int:
        return round(volume_in_ml * self.steps_per_ml) + self.offset_steps

    def _to_step_position(self, position: int, speed: int = ''):
        """ Absolute move to step position """
        return self.send_command_and_read_reply(ML600Commands.ABSOLUTE_MOVE, str(position), str(speed))

    def to_volume(self, volume_in_ml: float, speed: int = ''):
        """ Absolute move to volume """
        self._to_step_position(self._volume_to_step(volume_in_ml), speed)

    def pause(self):
        """ Pause any running command """
        return self.send_command_and_read_reply(ML600Commands.PAUSE)

    def resume(self):
        """ Resume any paused command """
        return self.send_command_and_read_reply(ML600Commands.RESUME)

    def stop(self):
        """ Stops and abort any running command """
        self.pause()
        return self.send_command_and_read_reply(ML600Commands.CLEAR_BUFFER)

    def wait_until_idle(self):
        """ Returns when no more commands are present in the pump buffer. """
        while self.is_busy:
            time.sleep(0.1)

    @property
    def version(self) -> str:
        """ Returns the current firmware version reported by the pump """
        return self.send_command_and_read_reply(ML600Commands.STATUS)

    @property
    def is_idle(self) -> bool:
        """ Checks if the pump is idle (not really, actually check if the last command has ended) """
        return self.send_command_and_read_reply(ML600Commands.REQUEST_DONE) == "Y"

    @property
    def is_busy(self) -> bool:
        """ Not idle """
        return not self.is_idle

    @property
    def firmware_version(self) -> str:
        """ Return firmware version """
        return self.send_command_and_read_reply(ML600Commands.FIRMWARE_VERSION)

    @property
    def valve_position(self) -> ValvePositionName:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum """
        return ML600.ValvePositionName(int(self.send_command_and_read_reply(ML600Commands.CURRENT_VALVE_POSITION)))

    @valve_position.setter
    def valve_position(self, target_position: ValvePositionName):
        self.send_command_and_read_reply(ML600Commands.VALVE_BY_NAME_CW, command_value=str(int(target_position)))

    def pickup(self, volume, from_valve: ValvePositionName, flowrate, wait):
        self.valve_position = from_valve
        pass

    def deliver(self, volume, from_valve, speed_out, wait):
        pass

    def transfer(self, volume, from_valve, to_valve, speed_in, speed_out, wait):
        pass


class TwoPumpAssembly(Thread):
    """
    Thread to control two pumps and have them generating a continuous flow.
    Note that the pumps should not be accessed directly when used in a TwoPumpAssembly!

    Notes: this needs to start a thread owned by the instance to control the pumps.
    The async version of this being possibly simpler w/ tasks and callback :)
    """

    def __init__(self, pump1: ML600, pump2: ML600, target_flowrate: float):
        super(TwoPumpAssembly, self).__init__()
        self._p1 = pump1
        self._p2 = pump2
        self.daemon = True
        self.cancelled = False
        self.flowrate = target_flowrate
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # While in principle possible, using syringes of different volumes is discouraged, hence...
        assert pump1.syringe_volume == pump2.syringe_volume, "Syringes w/ equal volume are needed for continuous flow!"
        # self._p1.initialize_pump()
        # self._p2.initialize_pump()

    def wait_for_both_pumps(self):
        """ Custom waiting method to wait a shorter time than normal (for better sync) """
        while self._p1.is_busy or self._p2.is_busy:
            time.sleep(0.01)  # 10ms sounds reasonable to me
        self.log.debug("Pumps ready!")

    def _speed(self):
        speed = self._p1.flowrate_to_seconds_per_stroke(self.flowrate)
        self.log.debug(f"Speed calculated as {speed}")
        return speed

    def run(self):
        """Overloaded Thread.run, runs the update
        method once per every 10 milliseconds."""

        while not self.cancelled:
            self._p1.valve_position = self._p1.ValvePositionName.OUTPUT
            self._p2.valve_position = self._p2.ValvePositionName.INPUT
            self.log.debug("Setting valves to target position... (phase 1)")
            self.wait_for_both_pumps()

            self._p1.to_volume(0, speed=self._speed())
            self._p2.to_volume(self._p2.syringe_volume, speed=self._speed())
            self.log.debug("Pumping... (phase 1)")
            self.wait_for_both_pumps()

            self._p1.valve_position = self._p1.ValvePositionName.INPUT
            self._p2.valve_position = self._p2.ValvePositionName.OUTPUT
            self.log.debug("Setting valves to target position... (phase 2)")
            self.wait_for_both_pumps()

            self._p1.to_volume(self._p1.syringe_volume, speed=self._speed())
            self._p2.to_volume(0, speed=self._speed())
            self.log.debug("Pumping... (phase 2)")
            self.wait_for_both_pumps()

    def cancel(self):
        """ Cancel continuous-pumping assembly """
        # SEND STOP COMMAND TO BOTH
        self.cancelled = True


if __name__ == '__main__':
    logging.basicConfig()
    l = logging.getLogger(__name__+".TwoPumpAssembly")
    # l = logging.getLogger(__name__)
    l.setLevel(logging.DEBUG)
    pump_connection = HamiltonPumpIO(7)
    test1 = ML600(pump_connection, syringe_volume=5)
    pump_connection2 = HamiltonPumpIO(8)
    test2 = ML600(pump_connection2, syringe_volume=5)

    metapump = TwoPumpAssembly(test1, test2, target_flowrate=20)
    metapump.start()
    time.sleep(20)
    metapump.flowrate = 1

    breakpoint()
