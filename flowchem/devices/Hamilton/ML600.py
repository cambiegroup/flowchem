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
from threading import Thread


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
    argument_string: Optional[str] = None

    def to_pump(self, address: int, argument: str = '') -> Protocol1Command:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        return Protocol1Command(target_pump_num=address, command_string=self.command_string,
                                argument_string=self.argument_string, command_argument=argument)


@dataclass
class Protocol1Command(Protocol1CommandTemplate):
    """ Class representing a pump command and its expected reply """
    # ':' is used for broadcast within the daisy chain.
    PUMP_ADDRESS = {pump_num: address for (pump_num, address) in enumerate(string.ascii_lowercase[:16], start=1)}
    REVERSED_PUMP_ADDRESS = {value: key for (key, value) in PUMP_ADDRESS.items()}
    # i.e. PUMP_ADDRESS = {1:"a", 2:"b"... }

    target_pump_num: Optional[int] = 1
    command_argument: Optional[str] = None

    def compile(self) -> str:
        """
        Create actual command byte by prepending pump address to command and appending executing command.
        """
        assert self.target_pump_num in range(1, 17)
        if self.command_argument:
            return str(self.PUMP_ADDRESS[self.target_pump_num]) + self.command_string + self.argument_string\
                   + self.command_argument + "R\r"
        else:
            return str(self.PUMP_ADDRESS[self.target_pump_num]) + self.command_string + "R\r"


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
    STATUS = Protocol1CommandTemplate(command_string="U")
    INIT_ALL = Protocol1CommandTemplate(command_string="X", argument_string="S")
    INIT_VALVE_ONLY = Protocol1CommandTemplate(command_string="LX")
    INIT_SYRINGE_ONLY = Protocol1CommandTemplate(command_string="X1", argument_string="S")


class ML600:
    """" ML600 implementation according to docs, to be tested! FIXME TODO

    From docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """
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

    def initialize_pump(self, speed: int = None):
        """
        Initialize both syringe and valve
        speed: 2-3692 is in seconds/stroke
        """
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL, parameter=str(speed))
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
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL, parameter=str(speed))
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL)

    def set_valve_position(self, target_position):
        pass

    def pickup(self, volume, from_valve, speed_in, wait):
        self.set_valve_position(from_valve)
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

        # While in principle possible, using syringes of different volumes is discouraged, hence...
        assert pump1.diameter == pump2.diameter, "Syringes with the same diameter are needed for continuous flow!"
        assert pump1.syringe_volume == pump2.syringe_volume, "Syringes w/ equal volume are needed for continuous flow!"

    def run(self):
        """Overloaded Thread.run, runs the update
        method once per every 10 milliseconds."""

        # Initialize both, homing and filling of pump 1

        while not self.cancelled:
            # SET PUMP1 TO 0
            # SET PUMP 2 TO FILL
            while self._p1.is_busy or self._p2.is_busy:
                time.sleep(0.005)  # 5ms sounds reasonable to me
            # SET PUMP1 TO 0
            # SET PUMP 2 TO FILL
            while self._p1.is_busy or self._p2.is_busy:
                time.sleep(0.005)  # 5ms sounds reasonable to me

    def cancel(self):
        """ Cancel continuous-pumping assembly """
        # SEND STOP COMMAND TO BOTH
        self.cancelled = True


if __name__ == '__main__':
    logging.basicConfig()
    l = logging.getLogger(__name__)
    l.setLevel(logging.DEBUG)
    pump_connection = HamiltonPumpIO(7)
    test = ML600(pump_connection, address=1)
    breakpoint()
