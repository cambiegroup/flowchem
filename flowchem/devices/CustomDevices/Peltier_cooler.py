from __future__ import annotations

from time import sleep

import logging
import threading
import warnings
from flowchem.constants import flowchem_ureg
from enum import Enum
from typing import Union, List, Optional, Tuple
from dataclasses import dataclass
from time import sleep
import serial


"""
Controlling Peltier via a TEC05-24 or TEC16-24 controller
"""

class PeltierException(Exception):
    """ General peltier exception """
    pass


class InvalidConfiguration(PeltierException):
    """ Used for failure in the serial communication """
    pass

class InvalidCommand(PeltierException):
    """ The provided command is invalid. This can be caused by the peltier state e.g. if boundary values are prohibitive! """
    pass


class InvalidArgument(PeltierException):
    """ A valid command was followed by an invalid argument, usually out of accepted range """

    pass


class UnachievableSetpoint(PeltierException):
    """ A valid command was followed by an invalid argument, Out of hardware capabilities """

    pass

@dataclass
class PeltierCommandTemplate:
    """ Class representing a peltier command and its expected reply, but without target peltier number """

    command_string: str
    reply_lines: int  # Reply line without considering leading newline and tailing prompt!
    requires_argument: bool

    def to_peltier(self, address: int, argument: int = "") -> PeltierCommand:
        """ Returns a Command by adding to the template peltier address and command arguments """
        if self.requires_argument and not argument:
            raise InvalidArgument(
                f"Cannot send command {self.command_string} without an argument!"
            )
        elif self.requires_argument is False and argument:
            raise InvalidArgument(
                f"Cannot provide an argument to command {self.command_string}!"
            )
        return PeltierCommand(
            command_string=self.command_string,
            reply_lines=self.reply_lines,
            requires_argument=self.requires_argument,
            target_peltier_address=address,
            command_argument=str(argument),
        )


@dataclass
class PeltierCommand(PeltierCommandTemplate):
    """ Class representing a peltier command and its expected reply """

    target_peltier_address: int
    command_argument: str

    def compile(self,) -> str:
        """
        Create actual command byte by prepending peltier address to command.
        """
        assert 0 <= self.target_peltier_address < 99
        # end character needs to be '\n'.
        if self.command_argument:
            return (
                str(self.target_peltier_address)
                + " "
                + self.command_string
                + " "
                + self.command_argument
                + "\n"
            )
        else:
            return (
                str(self.target_peltier_address)
                + " "
                + self.command_string
                + "\n"
            )


class PeltierIO:
    """ Setup with serial parameters, low level IO"""

    # noinspection PyPep8
    def __init__(self, port: Union[int, str], baud_rate: int = 115200):
        if baud_rate not in serial.serialutil.SerialBase.BAUDRATES:
            raise InvalidConfiguration(f"Invalid baud rate provided {baud_rate}!")

        if isinstance(port, int):
            port = f"COM{port}"
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.lock = threading.Lock()

        try:
            # noinspection PyPep8
            self._serial = serial.Serial(
                port=port, baudrate=baud_rate, timeout=0.1, parity="N", stopbits=1, bytesize=8
            )  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration from e

    def _write(self, command: PeltierCommand):
        """ Writes a command to the peltier """
        command = command.compile()
        self.logger.debug(f"Sending {repr(command)}")
        try:
            self._serial.write(command.encode("ascii"))
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration from e

    def _read_reply(self, command) -> str:
        """ Reads the peltier reply from serial communication """
        self.logger.debug(
            f"I am going to read {command.reply_lines} line for this command (+prompt)"
        )
        reply_string=""

        for line_num in range(
            command.reply_lines + 2
        ):  # +1 for leading newline character in reply + 1 for prompt
            chunk = self._serial.readline().decode("ascii")
            self.logger.debug(f"Read line: {repr(chunk)} ")

            # Stripping newlines etc allows to skip empty lines and clean output
            chunk = chunk.strip()

            if chunk:
                reply_string += chunk

        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    @staticmethod
    def parse_response_line(line: str) -> Tuple[int, str, float]:
        """ Split a received line in its components: address, prompt and reply body """
        assert len(line) > 0

        peltier_address = int(line.split(" ")[0])
        status= str(line.split(" ")[1].split("=")[0])
        reply = str(line.split(" ")[1].split("=")[1])

        return peltier_address, status, float(reply)

    @staticmethod
    def check_for_errors(last_response_line, command_sent):
        """ Further response parsing, checks for error messages """
        if "COMMAND ERR" in last_response_line:
            raise InvalidCommand(
                f"The command {command_sent} is invalid for Peltier {command_sent.target_peltier_address}!"
                f"[Reply: {last_response_line}]"
            )
        elif "NUMBER ERR" in last_response_line:
            raise InvalidArgument(
                f"The argument {command_sent} is out of allowed range for {command_sent.target_peltier_address}!"
                f"[Reply: {last_response_line}]"
            )
        elif "FORMAT ERR" in last_response_line:
            raise UnachievableSetpoint(
                f"The command {command_sent} to peltier {command_sent.target_peltier_address} is of invalid format, this likely means out of global boundaries"
                f"[Reply: {last_response_line}]"
            )


    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        try:
            self._serial.reset_input_buffer()
        except serial.PortNotOpenError as e:
            raise InvalidConfiguration from e

    def write_and_read_reply(
        self, command: PeltierCommand, return_parsed: bool = True
    ) -> Union[List[str], str]:
        """ Main PeltierIO method. Sends a command to the peltier, read the replies and returns it, optionally parsed """
        with self.lock:
            self.reset_buffer()
            self._write(command)
            response = self._read_reply(command)

        if not response:
            raise InvalidConfiguration(
                f"No response received from peltier, check peltier address! "
                f"(Currently set to {command.target_peltier_address})"
            )

        PeltierIO.check_for_errors(last_response_line=response, command_sent=command)

        # Parse reply
        peltier_address, return_status, parsed_response = PeltierIO.parse_response_line(response)

        # Ensures that all the replies came from the target peltier (this should always be the case)
        assert all(address == command.target_peltier_address for address in [peltier_address])

        return parsed_response if return_parsed else response


# noinspection SpellCheckingInspection
class PeltierCommands:

    """Holds the commands and arguments. """
    EMPTY_MESSAGE = PeltierCommandTemplate(
        command_string="", reply_lines=1, requires_argument=False
    )
    #TEMP1=-8.93 C
    GET_TEMPERATURE = PeltierCommandTemplate(
        command_string="GT1", reply_lines=1, requires_argument=False
    )
    # TEMP2 = -7.77C
    GET_SINK_TEMPERATURE = PeltierCommandTemplate(
        command_string="GT2", reply_lines=1, requires_argument=False
    )
    #TEMP_SET = 10.00 C ONLY WORKS IF ON
    SET_TEMPERATURE = PeltierCommandTemplate(
        command_string="STV", reply_lines=1, requires_argument=True
    )
    SET_SLOPE = PeltierCommandTemplate(
        command_string="STS", reply_lines=1, requires_argument=True
    )
    # STATUS=1
    SWITCH_ON = PeltierCommandTemplate(
        command_string="SEN", reply_lines=1, requires_argument=False
    )
    #STATUS=0
    SWITCH_OFF = PeltierCommandTemplate(
        command_string="SDI", reply_lines=1, requires_argument=False
    )
    COOLING_CURRENT_LIMIT = PeltierCommandTemplate(
        command_string="SCC", reply_lines=1, requires_argument=True
    )
    HEATING_CURRENT_LIMIT = PeltierCommandTemplate(
        command_string="SHC", reply_lines=1, requires_argument=True
    )
    SET_DIFFERENTIAL_PID = PeltierCommandTemplate(
        command_string="SDF", reply_lines=1, requires_argument=True
    )
    SET_INTEGRAL_PID = PeltierCommandTemplate(
        command_string="SIF", reply_lines=1, requires_argument=True
    )
    SET_PROPORTIONAL_PID = PeltierCommandTemplate(
        command_string="SPF", reply_lines=1, requires_argument=True
    )
    SET_T_MAX = PeltierCommandTemplate(
        command_string="SMA", reply_lines=1, requires_argument=True
    )
    SET_T_MIN = PeltierCommandTemplate(
        command_string="SMI", reply_lines=1, requires_argument=True
    )
    GET_POWER = PeltierCommandTemplate(
        command_string="GCU", reply_lines=1, requires_argument=False
    )
    GET_CURRENT = PeltierCommandTemplate(
        command_string="GPW", reply_lines=1, requires_argument=False
    )


class PeltierCooler:

    #TODO check sink temperature and throw error if to high - if not doable from controller

    heating_pid = [3,2,1]
    cooling_pid = [3,2,1]
    low_cooling_pid = [3,2,1]

    def __init__(self,
        peltier_io: PeltierIO,
        address: int = 0,
    ):
        self.peltier_io = peltier_io

        self.address: int = address

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by PumpIO
        self.log.info(
            f"Connected to peltier on port {self.peltier_io._serial.port}:{address}!")
        self.set_default_values()

    def set_default_values(self):
        self._set_current_limit_heating(10)
        self._set_current_limit_cooling(14)
        self._set_max_temperature(50)
        self._set_min_temperature(-55)
        self.set_pid_parameters(*self.cooling_pid)
        self.disable_slope()

    def send_command_and_read_reply( self, command_template: PeltierCommandTemplate, parameter: int= "", parse=True
    ) -> Union[str, List[str]]:
        """ Sends a command based on its template and return the corresponding reply as str """
        return self.peltier_io.write_and_read_reply(
            command_template.to_peltier(self.address, str(parameter)), return_parsed=parse
        )

    def set_temperature(self, temperature: float):
        self._set_state_dependant_pid_parameters(temperature)
        self._set_temperature(temperature)

    def _set_temperature(self, temperature: float):
        reply = self.send_command_and_read_reply(PeltierCommands.SET_TEMPERATURE, int(temperature*100))
        assert reply == temperature

    def set_slope(self, slope: float):
        reply = self.send_command_and_read_reply(PeltierCommands.SET_SLOPE, int(slope*100))
        assert reply == slope

    def disable_slope(self):
        reply = self.send_command_and_read_reply(PeltierCommands.SET_SLOPE, 0)
        assert reply == 0

    def start_control(self):
        reply = self.send_command_and_read_reply(PeltierCommands.SWITCH_ON)
        assert int(reply) == 1

    def get_temperature(self) -> float:
        reply = self.send_command_and_read_reply(PeltierCommands.GET_TEMPERATURE)
        assert type(reply) == float
        return reply

    def stop_control(self):
        reply = self.send_command_and_read_reply(PeltierCommands.SWITCH_OFF)
        assert int(reply) == 0

    def go_to_rt_and_switch_off(self):
        # set to RT, wait 2 min, stop T-control: This is just a convenience and safety measure: if the Peltier is
        # shut off and the heating is directly shut off, the heating might freeze
        self.set_temperature(25)
        sleep(120)
        self.stop_control()

    def get_power(self) -> int:
        # return power in W
        reply = int(self.send_command_and_read_reply(PeltierCommands.GET_POWER))
        return reply

    def get_current(self) -> int:
        # return power in W
        reply = self.send_command_and_read_reply(PeltierCommands.GET_CURRENT)
        assert type(reply)==float
        return reply

    def _set_current_limit_cooling(self, current_limit):
        # current in amp
        reply = self.send_command_and_read_reply(PeltierCommands.COOLING_CURRENT_LIMIT, int(current_limit*100))
        assert reply == current_limit

    def _set_current_limit_heating(self, current_limit):
        # current in amp
        reply = self.send_command_and_read_reply(PeltierCommands.HEATING_CURRENT_LIMIT, int(current_limit*100))
        assert reply == current_limit

    def set_pid_parameters(self, proportional, integral, differential):
        self._set_p_of_pid(proportional)
        self._set_i_of_pid(integral)
        self._set_d_of_pid(differential)

    def _set_d_of_pid(self, differential):
        # max 10
        reply = self.send_command_and_read_reply(PeltierCommands.SET_DIFFERENTIAL_PID, int(differential * 100))
        assert reply == differential

    def _set_i_of_pid(self, integral):
        # max 10
        reply = self.send_command_and_read_reply(PeltierCommands.SET_INTEGRAL_PID, int(integral * 100))
        assert reply == integral

    def _set_p_of_pid(self, proportional):
        # max 10
        reply = self.send_command_and_read_reply(PeltierCommands.SET_PROPORTIONAL_PID, int(proportional * 100))
        assert reply == proportional

    def _set_max_temperature(self, t_max):
        # max 10
        reply = self.send_command_and_read_reply(PeltierCommands.SET_T_MAX, int(t_max * 100))
        assert reply == t_max

    def _set_min_temperature(self, t_min):
        # max 10
        reply = self.send_command_and_read_reply(PeltierCommands.SET_T_MIN, int(t_min * 100))
        assert reply == t_min

    def _set_state_dependant_pid_parameters(self, new_T_setpoint):
        current_T = self.get_temperature()
        if current_T < new_T_setpoint:
            #set_heating_parameters
            self.set_pid_parameters(*self.heating_pid)
        else:
            if new_T_setpoint > -30:
                self.set_pid_parameters(*self.cooling_pid)
            else:
                self.set_pid_parameters(*self.low_cooling_pid)