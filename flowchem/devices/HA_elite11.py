from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Union, List, Dict, TypedDict
from dataclasses import dataclass

import serial


class Elite11Exception(Exception):
    pass


class InvalidConfiguration(Elite11Exception):
    pass


class NotConnectedError(Elite11Exception):
    pass


class Elite11PumpConfiguration(TypedDict):
    pass


@dataclass
class Protocol11CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """
    command_string: str
    reply_lines: int  # Including prompt!

    def to_pump(self, address: int) -> Protocol11Command:
        return Protocol11Command(command_string=self.command_string, reply_lines=self.reply_lines,
                                 target_pump_address=address)


@dataclass
class Protocol11Command(Protocol11CommandTemplate):
    """ Class representing a pump command and its expected reply """
    target_pump_address: int

    def compile(self, fast: bool = False) -> str:
        """
        Create actual command byte by prepending pump address to command.
        Fast saves some ms but do not update the display.
        """
        assert 0 < self.target_pump_address < 99
        if fast:
            return str(self.target_pump_address).zfill(2) + "@" + self.command_string
        else:
            return str(self.target_pump_address).zfill(2) + self.command_string


class PumpIO:
    """ Setup with serial parameters, low level IO"""
    VALID_PROMPTS = (":", ">", "<", "T")

    def __init__(self, port: str, baud_rate: int = 115200):
        if baud_rate not in serial.serialutil.SerialBase.BAUDRATES:
            raise InvalidConfiguration(f"Invalid baud rate provided {baud_rate}!")

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.lock = threading.Lock()

        self._serial = serial.Serial(port=port,baudrate=baud_rate, bytesize=serial.EIGHTBITS,
                                     parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1,
                                     xonxoff=False, rtscts=False, write_timeout=None, dsrdtr=False,
                                     exclusive=None)  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]

    def _write(self, command: Protocol11Command):
        """ Writes a command to the pump """
        command = command.compile(fast=False)
        self.logger.debug(f"Sending {command}")
        self._serial.write(command.encode("ascii"))

    def _read_reply(self, command) -> List[str]:
        """ Reads a line from the serial communication """
        reply_string = []
        for line in range(command.reply_lines):
            reply_string.append((self._serial.readline()).decode("ascii").strip())

        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def is_prompt_valid(self, prompt: str, command) -> bool:
        """ Verify absence of errors in prompt """
        assert 3 <= len(prompt) <= 4
        if not int(prompt[0:2]) == command.target_pump_address:
            raise Elite11Exception("Pump address mismatch in reply")

        if prompt[2:3] == "*":
            return False
        elif prompt[2:3] in self.VALID_PROMPTS:
            return True

    def flush_input_buffer(self):
        """ Flushes input buffer from potentially unread messages so that write and read works as expected """
        try:
            self._serial.reset_input_buffer()
        except serial.PortNotOpenError as e:
            raise NotConnectedError from e

    def write_and_read_reply(self, command: Protocol11Command):
        """  """
        with self.lock:
            self.flush_input_buffer()
            self._write(command)
            response = self._read_reply(command)
        if self.is_prompt_valid(response[-1], command):
            return response
        else:
            raise Elite11Exception(f"Invalid reply received from pump {command.target_pump_address}: {response}")

    @property
    def name(self):
        try:
            return self._serial.name
        except AttributeError:
            return None


class Elite11:
    """ Single pump object, implement commands w/ tenacity? """

    GET_VERSION = Protocol11CommandTemplate(command_string="VER", reply_lines=1)

    # FIXME use explicit diameter as default. (e.g. Our 10ml syringe?)
    def __init__(self, pump_io: PumpIO, address: int = 0, name: str = None, diameter: float = None):
        """Query model and version number of firmware to check pump is
        OK. Responds with a load of stuff, but the last three characters
        are XXY, where XX is the address and Y is pump status. :, > or <
        when stopped, running forwards, or running backwards. Confirm
        that the address is correct. This acts as a check to see that
        the pump is connected and working."""

        self.name = f"Pump {address}" if None else name
        self.pump_io = pump_io
        self.address = address  # This is converted to string and zfill()-ed in Protocol11Command
        self.diameter = None
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection. Failure handled by PumpIO
        self.get_version()
        self.log.info(f"Created pump '{self.name}' w/ address '{address}' on port {self.pump_io.name}!")

    def get_version(self):
        """ Returns the current firmware version reported by the pump """
        version = self.pump_io.write_and_read_reply(self.GET_VERSION.to_pump(self.address))
        return version


class PumpChain:
    """ Holds the pumps and can setup everything from JSON """
    def __init__(self, *pumps: Elite11):
        self.pumps = pumps
        self.pump_by_name = {}
        for pump in self.pumps:
            self.pump_by_name[pump.name] = pump

        # Check that pump_by_name is valid, i.e. holds the same number of object than pumps
        if len(self.pump_by_name.items()) != len(self.pumps):
            raise InvalidConfiguration("The pump names are not unique!")
