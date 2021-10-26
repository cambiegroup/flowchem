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

from flowchem.constants import InvalidConfiguration

@dataclass
class ViciProtocolCommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """

    command: str
    optional_parameter: str = ""
    execute_command: bool = True

    def to_valve(
        self, address: int, command_value: str = "", argument_value: str = ""
    ) -> ViciProtocolCommand:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        return ViciProtocolCommand(
            target_pump_num=address,
            command=self.command,
            optional_parameter=self.optional_parameter,
            command_value=command_value,
            argument_value=argument_value,
            execute_command=self.execute_command,
        )


@dataclass
class ViciProtocolCommand(ViciProtocolCommandTemplate):
    """ Class representing a pump command and its expected reply """

    VALVE_ADDRESS = {
        valve_num: address
        for (valve_num, address) in enumerate(string.ascii_lowercase[:16], start=1)
    }
    # i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}
    # Note ':' is used for broadcast within the daisy chain.

    target_valve_num: Optional[int] = 1
    command_value: Optional[str] = None
    argument_value: Optional[str] = None

    def compile(self) -> bytes:
        """ Create actual command byte by prepending valve address to command and appending executing command. """
        # TODO check
        assert self.target_valve_num in range(1, 99)
        if not self.command_value:
            self.command_value = ""

        compiled_command = (
            f"{self.VALVE_ADDRESS[self.target_valve_num]}"
            f"{self.command}{self.command_value}"
        )

        if self.argument_value:
            compiled_command += f"{self.optional_parameter}{self.argument_value}"
        # Add execution flag at the end
        if self.execute_command is True:
            compiled_command += "R"

        return (compiled_command + "\r").encode("ascii")

# TODO rest hast to be async sending and checking of reply