"""
This module is used to control Hamilton ML600 syringe pump via the protocol1/RNO+.
"""

from __future__ import annotations

import io
import string
import time

import serial
import logging
import threading
from dataclasses import dataclass
from typing import Union, List, Tuple, Optional
from serial import PARITY_EVEN, SEVENBITS, STOPBITS_ONE


class ML600Exception(Exception):
    """ General pump exception """
    pass


class InvalidConfiguration(ML600Exception):
    """ Used for failure in the serial communication """
    pass


class InvalidArgument(ML600Exception):
    """ A valid command was followed by an invalid argument, usually out of accepted range """
    pass


@dataclass
class Protocol1CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """
    command_string: str
    requires_argument: bool

    def to_pump(self, address: int, argument: str = '') -> Protocol1Command:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        if self.requires_argument and not argument:
            raise InvalidArgument(f"Cannot send command {self.command_string} without an argument!")
        elif self.requires_argument is False and argument:
            raise InvalidArgument(f"Cannot provide an argument to command {self.command_string}!")
        return Protocol1Command(command_string=self.command_string,
                                requires_argument=self.requires_argument, target_pump_num=address,
                                command_argument=argument)


@dataclass
class Protocol1Command(Protocol1CommandTemplate):
    """ Class representing a pump command and its expected reply """
    # ':' is used for broadcast within the daisy chain.
    PUMP_ADDRESS = {pump_num: address for (pump_num, address) in enumerate(string.ascii_lowercase[:16], start=1)}
    REVERSED_PUMP_ADDRESS = {value: key for (key, value) in PUMP_ADDRESS.items()}
    # i.e. PUMP_ADDRESS = {1:"a", 2:"b"... }

    target_pump_num: int
    command_argument: str

    def compile(self) -> str:
        """
        Create actual command byte by prepending pump address to command and appending executing command.
        """
        assert self.target_pump_num in range(1, 17)
        return str(self.PUMP_ADDRESS[self.target_pump_num]) + self.command_string + self.command_argument + "R\r"


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
            self._serial = serial.Serial(port=port, baudrate=baud_rate,
                                         timeout=0.1)  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration from e

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
        self._write("aXR\r")  # Broadcast: initialize + execute
        # Note: no need to consume reply here because:
        # - every command reset the buffer before writing
        # - the number of replies depends on the n of pumps connected (I believe)

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

    @staticmethod
    def parse_response(response: str) -> Tuple[bool, str]:
        """ Split a received line in its components: success, reply """

        if response[:1] == HamiltonPumpIO.ACKNOWLEDGE:
            success = True
        elif response[:1] == HamiltonPumpIO.NEGATIVE_ACKNOWLEDGE:
            success = False
        else:
            raise ML600Exception(f"This should not happen. Invalid reply: {response}!")

        return success, response[1:]

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
        success, parsed_response = HamiltonPumpIO.parse_response(response)

        assert success is True  # Well, this looks like a solid line ;)
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
    STATUS = Protocol1CommandTemplate(command_string="U", requires_argument=False)


class ML600:
    """" ML600 implementation according to docs, to be tested! FIXME TODO"""
    def __init__(self, pump_io: HamiltonPumpIO, address: int = 1, name: str = None, syringe_diameter: float = None,
                 syringe_volume: float = None):
        """

        Args:
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important
            syringe_diameter: ID of the syringe used (to translate linear motion to volume)
            syringe_volume: Needed to avoid over-withdrawing
        """
        self.pump_io = pump_io
        self.name = f"Pump {self.pump_io.name}:{address}" if name is None else name
        self.address: int = address
        if syringe_diameter is not None:
            self.diameter = syringe_diameter
        if syringe_volume is not None:
            self.syringe_volume = syringe_volume

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by HamiltonPumpIO
        # self.log.info(f"Connected to pump '{self.name}' on port {self.pump_io.name}:{address} version: {self.version}!")

    def send_command_and_read_reply(self, command_template: Protocol1CommandTemplate, parameter='') -> str:
        """ Sends a command based on its template and return the corresponding reply as str """
        return self.pump_io.write_and_read_reply(command_template.to_pump(self.address, parameter))

    @property
    def version(self) -> str:
        """ Returns the current firmware version reported by the pump """
        return self.send_command_and_read_reply(ML600Commands.STATUS)


if __name__ == '__main__':
    logging.basicConfig()
    l = logging.getLogger(__name__)
    l.setLevel(logging.DEBUG)
    pump_connection = HamiltonPumpIO(7)
    test = ML600(pump_connection, address=1)
    breakpoint()
