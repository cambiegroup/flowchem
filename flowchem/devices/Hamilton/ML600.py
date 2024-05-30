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
from typing import Union, Tuple, Optional
from serial import PARITY_EVEN, SEVENBITS, STOPBITS_ONE, PARITY_ODD
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

    # TODO move these two vars elsewhere!
    # ':' is used for broadcast within the daisy chain.
    PUMP_ADDRESS = {
        pump_num: address
        for (pump_num, address) in enumerate(string.ascii_lowercase[:16], start=1)
    }
    # # i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}

    target_pump_num: Optional[int] = 1
    command_value: Optional[str] = None
    argument_value: Optional[str] = None

    def compile(self, command_string: Optional = None) -> str:
        """
        Create actual command byte by prepending pump address to command and appending executing command.
        """
        assert self.target_pump_num in range(1, 17)
        if not command_string:
            command_string = self._compile()

        command_string = f"{self.PUMP_ADDRESS[self.target_pump_num]}" \
                         f"{command_string}"

        if self.execute_command is True:
            command_string += "R"

        return command_string + "\r"

    def _compile(self) -> str:
        """
        Create command string for individual pump. from that, up to two commands can be compiled, by appending pump address and adding run value
        """
        if not self.command_value:
            self.command_value = ""

        compiled_command = (
            f"{self.command}{self.command_value}"
        )
        if self.argument_value:
            compiled_command += f"{self.optional_parameter}{self.argument_value}"
        # Add execution flag at the end

        return compiled_command


class HamiltonPumpIO:
    """ Setup with serial parameters, low level IO"""

    ACKNOWLEDGE = chr(6)
    NEGATIVE_ACKNOWLEDGE = chr(21)

    def __init__(
        self,
        port: Union[int, str],
        baud_rate: int = 9600,
        hw_initialization: bool = True,
    ):
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
            self._serial = serial.Serial(
                port=port,
                baudrate=baud_rate,
                parity=PARITY_ODD,
                stopbits=STOPBITS_ONE,
                bytesize=SEVENBITS,
                timeout=0.1,
            )  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration(
                f"Check serial port availability! [{port}]"
            ) from e

        # noinspection PyTypeChecker
        self.sio = io.TextIOWrapper(
            buffer=io.BufferedRWPair(self._serial, self._serial),
            line_buffering=True,
            newline="\r",
        )

        # This has to be run after each power cycle to assign addresses to pumps
        self.num_pump_connected = self._assign_pump_address()
        if hw_initialization:
            self._hw_init()

    def _assign_pump_address(self) -> int:
        """
        To be run on init, auto assign addresses to pumps based on their position on the daisy chain!
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        self._write("1a\r")
        reply = self._read_reply()
        if reply and reply[:1] == "1":
            # reply[1:2] should be the address of the last pump. However, this does not work reliably.
            # So here we enumerate the pumps explicitly instead
            last_pump = 0
            for pump_num, address in Protocol1Command.PUMP_ADDRESS.items():
                self._write(f"{address}UR\r")
                if "NV01" in self._read_reply():
                    last_pump = pump_num
                else:
                    break
            self.logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
            return int(last_pump)
        else:
            raise InvalidConfiguration(f"No pump available on {self._serial.port}")

    def _hw_init(self):
        """ Send to all pumps the HW initialization command (i.e. homing) """
        self._write(":KR\r")
        self._write(":VR\r")# Broadcast: initialize + execute
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

    def write_and_read_reply(self, command: list[Protocol1Command] | Protocol1Command) -> str:

        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        command_compiled = ""
        with self.lock:
            self.reset_buffer()
            if type(command) != list:
                command = [command]
            for com in command:
                command_compiled += com._compile()
            com_comp = com.compile(command_compiled)
            self._write(com_comp)
            response = self._read_reply()

        if not response:
            raise InvalidConfiguration(
                f"No response received from pump, check pump address! "
                f"(Currently set to {command[0].target_pump_num})"
            )

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

    # only works for pumps with two syringe drivers
    SET_VALVE_CONTINUOUS_DISPENSE = Protocol1CommandTemplate(command="LST19")
    # only works for pumps with two syringe drivers
    SET_VALVE_DUAL_DILUTOR = Protocol1CommandTemplate(command="LST20")
    # if there are two drivers, both sides can be selected
    SELECT_LEFT_SYRINGE = Protocol1CommandTemplate(command="B")
    SELECT_RIGHT_SYRINGE = Protocol1CommandTemplate(command="C")

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
    SYRINGE_DEFAULT_SPEED = Protocol1CommandTemplate(
        command="YQS"
    )  # 2-3692 seconds per stroke
    CURRENT_SYRINGE_POSITION = Protocol1CommandTemplate(command="YQP")  # 0-52800 steps
    SYRINGE_DEFAULT_BACKOFF = Protocol1CommandTemplate(command="YQB")  # 0-1000 steps, these are per feault 80 for <= 1mL and 96 above. This is just the distance that the plunger retracts after initialisation reaches the overload point. This is done to not compress the plunger
    CURRENT_VALVE_POSITION = Protocol1CommandTemplate(
        command="LQP"
    )  # 1-8 (see docs, Table 3.2.2)
    GET_RETURN_STEPS = Protocol1CommandTemplate(command="YQN")  # 0-1000 steps
    # PARAMETER CHANGE
    SET_RETURN_STEPS = Protocol1CommandTemplate(command="YSN")  # 0-1000, return steps increase accuracy and precision. This is done by moving past the syringe position setpoint and then moving back the amount of set steps. This reduces mechanical system backlash
    # VALVE REQUEST
    VALVE_ANGLE = Protocol1CommandTemplate(command="LQA")  # 0-359 degrees
    VALVE_CONFIGURATION = Protocol1CommandTemplate(
        command="YQS"
    )  # 11-20 (see docs, Table 3.2.2)
    #Set valve speed
    SET_VALVE_SPEED = Protocol1CommandTemplate(command="LSF")  # 15-720 degrees per sec
    #Set valve speed
    GET_VALVE_SPEED = Protocol1CommandTemplate(command="LQF")
    # TIMER REQUEST
    TIMER_DELAY = Protocol1CommandTemplate(command="<T")  # 0–99999999 ms
    # FIRMWARE REQUEST
    FIRMWARE_VERSION = Protocol1CommandTemplate(
        command="U"
    )  # xxii.jj.k (ii major, jj minor, k revision)


class ML600:
    """" ML600 implementation according to docs. Tested on 61501-01 (single syringe).

    From docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """
    # TODO the "dirty approach" to use both valves is actually setting to continuous pumping, then input and output can be selected, however on the right syringe the input and output are reverted (or one swaps the tubing...)
    # Anyway, valves should be switched by degree and not by name, but one needs to know and be sure which exact valve was initialized
    class ValvePositionName(IntEnum):
        """ Maps valve position to the corresponding number """

        POSITION_1 = 1
        # POSITION_2 = 2
        POSITION_3 = 3
        INPUT = 9  # 9 is default inlet, i.e. 1
        OUTPUT = 10  # 10 is default outlet, i.e. 3
        WASH = 11  # 11 is default wash, i.e. undefined

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
        syringe_volume: float or dict,
        address: int = 1,
        name: str = None,
            return_steps = 0
    ):
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
        self.is_single=self.is_single_syringe()
        if isinstance(syringe_volume, (int, float)):
            if self.is_single:
                syringe_volume = {"left": syringe_volume, "right": None}
            else:
                syringe_volume = {"left": syringe_volume, "right": syringe_volume}
        elif type(syringe_volume) is dict:
            assert "left" and "right" in syringe_volume.keys(), "Left syringe volume not specified"
        for syr_vol in syringe_volume.values():
            if syr_vol is not None and syr_vol not in ML600.VALID_SYRINGE_VOLUME:
                raise InvalidConfiguration(
                    f"The specified syringe volume ({syringe_volume}) does not seem to be valid!\n"
                    f"The volume in ml has to be one of {ML600.VALID_SYRINGE_VOLUME}"
                )
        self.syringe_volume = syringe_volume

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        self.cancelled = threading.Event()
        self.pumping_thread = None
        self.daemon = True
        self.return_steps = return_steps# Steps added to each absolute move command, to decrease wear and tear at volume = 0, 24 is manual default
        # This command is used to test connection: failure handled by HamiltonPumpIO
        self.log.info(
            f"Connected to pump '{self.name}'  FW version: {self.firmware_version}!"
        )

    def steps_per_ml(self, syringe: str or None) -> int:
        """ Returns the number of steps per ml for the given syringe """
        if syringe is None:
            if self.is_single:
                syringe = "left"
            elif self.syringe_volume["left"] == self.syringe_volume["right"]:
                syringe = "left"
            else:
                raise ValueError("Syringe not specified, but pump has different syringe volumes")
        return 48000 / self.syringe_volume[syringe]
    
    def is_single_syringe(self) -> bool:
        return self.send_command_and_read_reply(ML600Commands.IS_SINGLE_SYRINGE) == "Y"

    def send_command_and_read_reply(
        self,
        command_template: Protocol1CommandTemplate,
        command_value="",
        argument_value="",
            syringe=None,
    ) -> str:
        """ Sends a command based on its template and return the corresponding reply as str """
        if syringe == "left":
            syringe_select = ML600Commands.SELECT_LEFT_SYRINGE
        elif syringe == "right":
            syringe_select = ML600Commands.SELECT_RIGHT_SYRINGE
        elif syringe == None:
            return self.pump_io.write_and_read_reply([
                self.create_single_command(command_template, command_value, argument_value),
            ])
        else:
            raise NotImplementedError(f"Choose left or right as syringe argument, you chose {syringe}.")
        return self.pump_io.write_and_read_reply([
            self.create_single_command(syringe_select),
            self.create_single_command(command_template, command_value, argument_value),
                                                  ])

    def create_single_command(
            self,
            command_template: Protocol1CommandTemplate,
            command_value: str or int="",
            argument_value="",
    ) -> Protocol1Command:
        # if this holds a list of dictionaries, that specify
        """ This creates a single command of which a list (so multiple commands) can be sent to device. Just hand a
        list of multiple so created commands to """

        x = command_template.to_pump(self.address, command_value, argument_value)
        return x

    def send_multiple_commands(self, list_of_commands: [Protocol1Command]) -> str:
        return self.pump_io.write_and_read_reply(list_of_commands)

    def initialize_pump(self, flowrate: int, syringe:str = None):
        """
        Initialize both syringe and valve on specified side
        speed: flowrate in mL/min
        """
        self.send_command_and_read_reply(ML600Commands.CLEAR_BUFFER, syringe=syringe)

        speed = self.flowrate_to_seconds_per_stroke(flowrate, syringe=syringe)
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(
                ML600Commands.INIT_ALL, argument_value=str(speed), syringe=syringe
            )
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL, syringe=syringe)

    def initialize_valve(self, syringe=None):
        """
        Initialize valve only
        """
        return self.send_command_and_read_reply(ML600Commands.INIT_VALVE_ONLY, syringe=syringe)

    def initialize_syringe(self, flowrate: int, syringe="left"):
        """
        Initialize syringe on specified side only
        speed: 2-3692 is in seconds/stroke
        """
        speed = self.flowrate_to_seconds_per_stroke(flowrate, syringe=syringe)
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(
                ML600Commands.INIT_SYRINGE_ONLY, argument_value=str(speed), syringe=syringe
            )
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_SYRINGE_ONLY, syringe=syringe)

# todo if this selects none, it should wwork but only if both syringes are same size
    def flowrate_to_seconds_per_stroke(self, flowrate_in_ml_min: float, syringe=None):
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
        flowrate_in_steps_sec = flowrate_in_ml_sec * self.steps_per_ml(syringe)
        seconds_per_stroke = round(48000 / flowrate_in_steps_sec)
        assert 2 <= seconds_per_stroke <= 3692
        return round(seconds_per_stroke)

    # todo if this selects none, it should wwork but only if both syringes are same size
    def _volume_to_step(self, volume_in_ml: float, syringe=None) -> int:
        return round(volume_in_ml * self.steps_per_ml(syringe))

    # todo if this selects none, it should wwork but only if both syringes are same size
    def _to_step_position(self, position: int, speed: int = "", syringe="left"):
        """ Absolute move to step position """
        assert syringe in ["left", "right"], f"Choose left or right as syringe argument, you chose {syringe}. "
        return self.send_command_and_read_reply(
            ML600Commands.ABSOLUTE_MOVE, str(position), str(speed), syringe=syringe
        )

    # todo if this selects none, it should wwork but only if both syringes are same size
    def to_volume(self, volume_in_ml: float, flow_rate: int = "", syringe="left"):
        """ Absolute move to volume, so no matter what volume is now, it will move to this volume.
        This is bad for dosing, but good for general pumping"""
        speed = self.flowrate_to_seconds_per_stroke(flow_rate, syringe=syringe)
        position = self._volume_to_step(volume_in_ml, syringe)
        self._to_step_position(position, speed, syringe=syringe)
        self.log.debug(
            f"Pump {self.name} set to volume {volume_in_ml} at speed {flow_rate}"
        )

    def pause(self, syringe=None):
        """ Pause any running command """
        return self.send_command_and_read_reply(ML600Commands.PAUSE, syringe=syringe)

    def resume(self, syringe=None):
        """ Resume any paused command """
        return self.send_command_and_read_reply(ML600Commands.RESUME, syringe=syringe)

    def stop(self, syringe=None):
        """ Stops and abort any running command """
        self.pause(syringe=syringe)
        return self.send_command_and_read_reply(ML600Commands.CLEAR_BUFFER, syringe=syringe)

    def wait_until_idle(self, syringe=None):
        """ Returns when no more commands are present in the pump buffer. """
        self.log.debug(f"Pump {self.name} wait until idle")
        while self.is_busy(syringe=syringe):
            time.sleep(0.001)

    @property
    def version(self) -> str:
        """ Returns the current firmware version reported by the pump """
        return self.send_command_and_read_reply(ML600Commands.STATUS)

    def is_idle(self, syringe=None) -> bool:
        """ Checks if the pump is idle (not really, actually check if the last command has ended) """
        return self.send_command_and_read_reply(ML600Commands.REQUEST_DONE, syringe=syringe) == "Y"

    def is_busy(self, syringe=None) -> bool:
        """ Not idle """
        return not self.is_idle(syringe=syringe)

    @property
    def firmware_version(self) -> str:
        """ Return firmware version """
        return self.send_command_and_read_reply(ML600Commands.FIRMWARE_VERSION)

    @property
    def valve_position(self) -> ValvePositionName:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum """
        return ML600.ValvePositionName(
            int(self.send_command_and_read_reply(ML600Commands.CURRENT_VALVE_POSITION))
        )

    @valve_position.setter
    def valve_position(self, target_position: ValvePositionName):
        self.log.debug(f"{self.name} valve position set to {target_position.name}")
        self.send_command_and_read_reply(
            ML600Commands.VALVE_BY_NAME_CW, command_value=str(int(target_position))
        )
        self.wait_until_idle()

    @property
    def return_steps(self) -> int:
        """ Gives the dfined return steps for syringe movement """
        return int(self.send_command_and_read_reply(ML600Commands.GET_RETURN_STEPS))

    @return_steps.setter
    def return_steps(self, return_steps: int):
        # waiting is necessary since this happens on (class) initialisation
        self.wait_until_idle()
        self.send_command_and_read_reply(
            ML600Commands.SET_RETURN_STEPS, command_value=str(int(return_steps)), syringe="left"
        )
        if not self.is_single:
            self.send_command_and_read_reply(
                ML600Commands.SET_RETURN_STEPS, command_value=str(int(return_steps)), syringe="right"
            )

    def syringe_position(self, syringe="left"):
        """ Returns the current position of the syringe in ml """
        # todo this only should work with specified syringe
        if syringe not in ["left", "right"] and not self.is_single:
            raise ValueError("Syringe must be specified as either 'left' or 'right'")
        current_steps = int(
            self.send_command_and_read_reply(ML600Commands.CURRENT_SYRINGE_POSITION, syringe=syringe))
        return current_steps / self.steps_per_ml(syringe)

    def _absolute_syringe_move(self, volume, flow_rate, syringe:str="left") -> List[str]:
        """ Absolute move to volume, so no matter what volume is now, it will move to this volume.
        This is bad for dosing, but good for general pumping"""
        speed = self.flowrate_to_seconds_per_stroke(flow_rate, syringe=syringe)
        position = self._volume_to_step(volume, syringe)
        if syringe in ["left", "right"]:
            selection = [self.create_single_command(ML600Commands.SELECT_LEFT_SYRINGE) if syringe == "left" else self.create_single_command(ML600Commands.SELECT_RIGHT_SYRINGE)]
        else:
            raise ValueError("Syringe must be specified as either 'left' or 'right'")
        selection.append(self.create_single_command(ML600Commands.ABSOLUTE_MOVE, str(position), str(speed)))
        return selection

    def fill_single_syringe(self, volume:float, speed, valve_angle = 180, syringe="left"):
        """
        Fill a single syringe. This should also work on dual syringe, but only for the left one.
        Assumes Input and output on the right so the valve is not used here


        Args:
            volume:
            speed:

        Returns:

        """
        # switch valves
        assert syringe in ["left", "right"], "Either select left or right syringe"
        self.wait_until_idle(syringe=syringe)
        # easy to get working on right one: just make default variable for right or left
        self.switch_valve_by_angle(valve_angle, syringe=syringe)
        self.wait_until_idle(syringe=syringe)
        # actuate syringes
        curr_vol = self.syringe_position(syringe=syringe)
        to_vol = round(curr_vol + volume, 3)
        self.to_volume(to_vol, speed, syringe=syringe)


    def deliver_from_single_syringe(self, volume_to_deliver:float, speed, valve_angle=180, syringe="left"):
        """
        Assumes Input and output on the right so the valve is not used here

        Args:
            volume_to_deliver:
            speed:
            syringe:

        Returns:

        """
        # switch valves
        if syringe == "left":
            syringe_select = ML600Commands.SELECT_LEFT_SYRINGE
        elif syringe == "right":
            syringe_select = ML600Commands.SELECT_RIGHT_SYRINGE
        else:
            raise NotImplementedError(f"Choose left or right as syringe argument, you chose {syringe}.")

        self.wait_until_idle(syringe=syringe)
        self.switch_valve_by_angle(valve_angle, syringe=syringe)
        # actuate syringes
        self.wait_until_idle(syringe=syringe)
        curr_vol = self.syringe_position(syringe=syringe)
        to_vol = round(curr_vol - volume_to_deliver, 3)
        self.to_volume(to_vol, speed, syringe=syringe)

    def switch_valve_by_angle(self, angle, syringe="left"):
        self.send_command_and_read_reply(ML600Commands.VALVE_BY_ANGLE_CW, command_value=angle, syringe=syringe)

    def home_single_syringe(self, speed, syringe="left", valve_angle = 180):
        """
                Assumes Input on left of valve and output on the right

        Args:
            speed:
            syringe:

        Returns:

        """
        # switch valves
        self.wait_until_idle(syringe=syringe)
        self.switch_valve_by_angle(valve_angle, syringe=syringe)
        # actuate syringes
        self.wait_until_idle(syringe=syringe)
        self.to_volume(0, speed, syringe=syringe)

    def fill_dual_syringes(self, volume, speed):
        """
        Assumes Input on left of valve and output on the right
        """
        # switch valves
        assert self.syringe_volume["left"] == self.syringe_volume["right"], "Syringes are not the same size, this can create unexpected behaviour"
        self.wait_until_idle(syringe=None)
        self.send_multiple_commands([
            self.create_single_command(ML600Commands.SELECT_LEFT_SYRINGE),
            self.create_single_command(ML600Commands.VALVE_BY_ANGLE_CW, command_value="0"),
            self.create_single_command(ML600Commands.SELECT_RIGHT_SYRINGE),
            self.create_single_command(ML600Commands.VALVE_BY_ANGLE_CW, command_value="0"),
        ])
        self.wait_until_idle(syringe=None)
        # actuate syringes
        self.send_multiple_commands(
            self._absolute_syringe_move(volume, speed, syringe="left") +
            self._absolute_syringe_move(volume, speed, syringe="right")
        )


    def deliver_from_dual_syringes(self, to_volume:float, speed:float):
        """
        Assumes Input on left of valve and output on the right

        Args:
            to_volume:
            speed:

        Returns:

        """
        assert self.syringe_volume["left"] == self.syringe_volume["right"], "Syringes are not the same size, this can create unexpected behaviour"
        # switch valves
        self.wait_until_idle(syringe=None)
        self.send_multiple_commands([
            self.create_single_command(ML600Commands.SELECT_LEFT_SYRINGE),
            self.create_single_command(ML600Commands.VALVE_BY_ANGLE_CCW, command_value=135),
            self.create_single_command(ML600Commands.SELECT_RIGHT_SYRINGE),
            self.create_single_command(ML600Commands.VALVE_BY_ANGLE_CCW, command_value=135),
        ])
        # actuate syringes
        self.wait_until_idle(syringe=None)
        self.send_multiple_commands(
            self._absolute_syringe_move(to_volume, speed, syringe="left")+
            self._absolute_syringe_move(to_volume, speed, syringe="right"))


if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger(__name__ + ".TwoPumpAssembly")
    log.setLevel(logging.DEBUG)
    log = logging.getLogger(__name__ + ".ML600")
    log.setLevel(logging.DEBUG)
    pump_connection = HamiltonPumpIO(41)
    test1 = ML600(pump_connection, syringe_volume=5, address=1)
    test2 = ML600(pump_connection, syringe_volume=5, address=2)
    metapump = TwoPumpAssembly(test1, test2, target_flowrate=15, init_seconds=20)
    metapump.start()
    input()
