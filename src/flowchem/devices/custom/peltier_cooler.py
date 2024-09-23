""" Control module for Peltier cooler via a TEC05-24 or TEC16-24 controller """
from __future__ import annotations

import aioserial
import pint
import numpy as np

from typing import Union, List, Tuple
from dataclasses import dataclass
from time import sleep

from loguru import logger
from asyncio import Lock
from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.components.technical.temperature import TempRange
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.custom.peltier_cooler_component import (
    PeltierCoolerTemperatureControl,
)
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import jakob, miguel


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

    def compile(self, ) -> str:
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
        logger.debug(f"Sending {repr(command)}")
        try:
            await self._serial.write_async(command.encode("ascii"))
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

    async def _read_reply(self, command) -> str:
        """ Reads the peltier reply from serial communication """
        logger.debug(
            f"I am going to read {command.reply_lines} line for this command (+prompt)"
        )
        reply_string = ""

        for line_num in range(
            command.reply_lines + 2
        ):  # +1 for leading newline character in reply + 1 for prompt
            chunk = await self._serial.readline_async()
            chunk = chunk.decode("ascii")
            logger.debug(f"Read line: {repr(chunk)} ")

            # Stripping newlines etc allows to skip empty lines and clean output
            chunk = chunk.strip()

            if chunk:
                reply_string += chunk

        logger.debug(f"Reply received: {reply_string}")
        return reply_string

    @staticmethod
    def parse_response_line(line: str) -> Tuple[int, str, float or str]:
        """ Split a received line in its components: address, prompt and reply body """
        assert len(line) > 0

        peltier_address = int(line.split(" ")[0])
        status = str(line.split(" ")[1].split("=")[0])
        reply = str(line.split(" ")[1].split("=")[1])
        try:
            return peltier_address, status, float(reply)
        except ValueError:
            return peltier_address, status, str(reply)

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
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

    async def write_and_read_reply(
        self, command: PeltierCommand, return_parsed: bool = True
    ) -> Union[List[str], str]:
        """ Main PeltierIO method. Sends a command to the peltier, read the replies and returns it, optionally parsed """
        async with self.lock:
            self.reset_buffer()
            await self._write(command)
            response = await self._read_reply(command)

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
    # TEMP1=-8.93 C
    GET_TEMPERATURE = PeltierCommandTemplate(
        command_string="GT1", reply_lines=1, requires_argument=False
    )
    # TEMP2 = -7.77C
    GET_SINK_TEMPERATURE = PeltierCommandTemplate(
        command_string="GT2", reply_lines=1, requires_argument=False
    )
    # TEMP_SET = 10.00 C ONLY WORKS IF ON
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
    # STATUS=0
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
    GET_SETTINGS = PeltierCommandTemplate(
        command_string="GPA", reply_lines=1, requires_argument=False
    )


class PeltierDefaults:
    HEATING_PID = [0.64, 0.53, 0.13]
    COOLING_PID = [2.83, 2.36, 0.59]
    BASE_TEMP = -7.6
    STATE_DEPENDANT_CURRENT_LIMITS = np.array([[-55, 50], [14, 14], [10, 10]]).transpose()
    T_MAX = 50
    T_MIN = -55


class PeltierLowCoolingDefaults(PeltierDefaults):
    HEATING_PID = [2, 0.03, 0]
    COOLING_PID = HEATING_PID
    BASE_TEMP = -24.7
    STATE_DEPENDANT_CURRENT_LIMITS = np.array(
        [[-65, -60, -55, -50, -40, -30, -20, -10, 0, 10, 20,30], [7.5, 6.5, 5, 4, 3, 3, 1, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0.5, 1, 1, 2.5, 3, 3.5, 3.5, 3.5]]).transpose()
    T_MAX = 30
    T_MIN = -66


class PeltierCooler:

    def __init__(self,
        peltier_io: PeltierIO,
        peltier_defaults: PeltierDefaults,
        address: int = 0
    ):
        self.peltier_io = peltier_io

        self.address: int = address

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by PumpIO
        self.log.info(
            f"Connected to peltier on port {self.peltier_io._serial.port}:{address}!")
        self.peltier_defaults = peltier_defaults
        self.set_default_values()
        self.set_pid_parameters(*self.peltier_defaults.COOLING_PID)

    def set_default_values(self):
        self._set_max_temperature(self.peltier_defaults.T_MAX)
        self._set_min_temperature(self.peltier_defaults.T_MIN)
        self._set_current_limit_heating(int(self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[-1::,2]))
        self._set_current_limit_cooling(int(self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[:1:,1]))
        self.disable_slope()

    def send_command_and_read_reply( self, command_template: PeltierCommandTemplate, parameter: int= "", parse=True
    ) -> Union[str, List[str]]:
    async def set_default_values(self):
        await self._set_max_temperature(self.peltier_defaults.T_MAX)
        await self._set_min_temperature(self.peltier_defaults.T_MIN)
        await self._set_current_limit_heating(int(self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[-1::, 2]))
        await self._set_current_limit_cooling(int(self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[:1:, 1]))
        await self.disable_slope()

    async def set_pid_parameters(self, proportional, integral, differential):
        await self._set_p_of_pid(proportional)
        await self._set_i_of_pid(integral)
        await self._set_d_of_pid(differential)

    async def send_command_and_read_reply(self, command_template: PeltierCommandTemplate, parameter: int = "", parse=True
                                    ) -> Union[str, List[str]]:
        """ Sends a command based on its template and return the corresponding reply as str """
        return await self.peltier_io.write_and_read_reply(
            command_template.to_peltier(self.address, str(parameter)), return_parsed=parse
        )

    async def set_temperature(self, temperature: pint.Quantity):
        await self.stop_control()
        # start softly
        await self._set_current_limit_cooling(0.5)
        await self._set_current_limit_heating(0.5)
        await self._set_temperature(temperature.m_as("°C"))
        await self.start_control()
        sleep(10)
        # Now start with power
        await self.set_default_values()
        await self._set_state_dependant_parameters(temperature.m_as("°C"))

    async def _set_temperature(self, temperature: float):
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_TEMPERATURE, round(temperature * 100))
        assert reply == temperature

    async def set_slope(self, slope: float):
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_SLOPE, round(slope * 100))
        assert reply == slope

    async def disable_slope(self):
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_SLOPE, 0)
        assert reply == 0

    async def start_control(self):
        reply = await self.send_command_and_read_reply(PeltierCommands.SWITCH_ON)
        assert int(reply) == 1

    async def get_temperature(self) -> float:
        reply = await self.send_command_and_read_reply(PeltierCommands.GET_TEMPERATURE)
        assert isinstance(reply, float)
        return reply

    async def get_sink_temperature(self) -> float:
        reply = await self.send_command_and_read_reply(PeltierCommands.GET_SINK_TEMPERATURE)
        assert isinstance(reply, float)
        return reply

    async def stop_control(self):
        reply = await self.send_command_and_read_reply(PeltierCommands.SWITCH_OFF)
        assert int(reply) == 0

    async def go_to_rt_and_switch_off(self):
        # set to RT, wait 2 min, stop T-control: This is just a convenience and safety measure: if the Peltier is
        # shut off and the heating is directly shut off, the heating might freeze
        await self.set_temperature(25)
        sleep(120)
        await self.stop_control()

    async def get_power(self) -> int:
        # return power in W
        reply = int(await self.send_command_and_read_reply(PeltierCommands.GET_POWER))
        return reply

    async def get_current(self) -> int:
        # return power in W
        reply = await self.send_command_and_read_reply(PeltierCommands.GET_CURRENT)
        assert isinstance(reply, float)
        return reply

    async def get_parameters(self) -> str:
        # return parameter list
        reply = await self.send_command_and_read_reply(PeltierCommands.GET_SETTINGS)
        return reply

    async def _set_current_limit_cooling(self, current_limit):
        # current in amp
        reply = await self.send_command_and_read_reply(PeltierCommands.COOLING_CURRENT_LIMIT, round(current_limit * 100))
        assert reply == current_limit

    async def _set_current_limit_heating(self, current_limit):
        # current in amp
        reply = await self.send_command_and_read_reply(PeltierCommands.HEATING_CURRENT_LIMIT, round(current_limit * 100))
        assert reply == current_limit

    async def _set_d_of_pid(self, differential):
        # max 10
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_DIFFERENTIAL_PID, round(differential * 100))
        assert reply == differential

    async def _set_i_of_pid(self, integral):
        # max 10
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_INTEGRAL_PID, round(integral * 100))
        assert reply == integral

    async def _set_p_of_pid(self, proportional):
        # max 10
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_PROPORTIONAL_PID, round(proportional * 100))
        assert reply == proportional

    async def _set_max_temperature(self, t_max):
        # max 10
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_T_MAX, round(t_max * 100))
        assert reply == t_max

    async def _set_min_temperature(self, t_min):
        # max 10
        reply = await self.send_command_and_read_reply(PeltierCommands.SET_T_MIN, round(t_min * 100))
        assert reply == t_min

    async def _set_state_dependant_parameters(self, new_T_setpoint):
        if self.peltier_defaults.BASE_TEMP < new_T_setpoint:
            # set_heating_parameters
            await self.set_pid_parameters(*self.peltier_defaults.HEATING_PID)
        else:
            await self.set_pid_parameters(*self.peltier_defaults.COOLING_PID)
        if new_T_setpoint > self.peltier_defaults.BASE_TEMP:
            # set current limit for heating
            settings = self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[
                np.where((self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[::, 0] >= new_T_setpoint))[0][0]]

        else:
            # set to cooling
            settings = self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[
                np.where((self.peltier_defaults.STATE_DEPENDANT_CURRENT_LIMITS[::, 0] <= new_T_setpoint))[0][-1]]
        await self._set_current_limit_cooling(settings[1])
        await self._set_current_limit_heating(settings[2])

