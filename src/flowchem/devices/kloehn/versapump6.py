"""Control Hamilton ML600 syringe pump via the protocol1/RNO+."""
from __future__ import annotations

import pandas as pd
import sys
sys.path.append('C:\\Users\\mgarcia\\Documents\\github\\flowchem\\src')

import asyncio
import string
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aioserial
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.kloehn.versapump6_pump import VersaPump6Pump
from flowchem.devices.kloehn.versapump6_valve import VersaPump6Valve
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import miguel

if TYPE_CHECKING:
    import pint

# i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}
# Creating a dictionary with the predefined values
PUMP_ADDRESS = {
    1: '1',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9',
    10: ':',
    11: ';',
    12: '<',
    13: '=',
    14: '>',
    15: '?'
}
@dataclass
class DTProtocolCommand:
    """Class representing a pump command and its expected reply."""

    command: str
    start_character: str = "/"
    address_character: int = 1
    carriage_return: str = "<CR>"

    def compile(self) -> str:
        """Create actual command byte by prepending pump address to command and appending executing command."""
        compiled_command = (
            f"{self.start_character}"
            f"{PUMP_ADDRESS[self.address_character]}"
            f"{self.command}"
            f"{self.carriage_return}"
        )

        return compiled_command


class VersaPump6IO:
    """Setup with serial parameters, low level IO."""


    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_ODD,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.Serial) -> None:
        """Initialize serial port, not pumps."""
        self._serial = aio_port
        self.num_pump_connected: int | None = (
            None  # Set by `HamiltonPumpIO.initialize()`
        )

    @classmethod
    def from_config(cls, config):
        """Create HamiltonPumpIO from config."""
        configuration = VersaPump6IO.DEFAULT_CONFIG | config

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the pump on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)

    async def initialize(self, hw_initialization: bool = True):
        """Ensure connection with pump and initialize it (if hw_initialization is True)."""
        self.num_pump_connected = await self._assign_pump_address()
        if hw_initialization:
            await self._hw_init()
        await self._is_single_syringe()

    async def _assign_pump_address(self) -> int:
        """Auto assign pump addresses.

        To be run on init, auto assign addresses to pumps based on their position in the daisy chain.
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        try:
            await self._write_async(b"1a\r")
        except aioserial.SerialException as e:
            raise InvalidConfigurationError from e

        reply = await self._read_reply_async()
        if not reply or reply[:1] != "1":
            raise InvalidConfigurationError(f"No pump found on {self._serial.port}")
        # reply[1:2] should be the address of the last pump. However, this does not work reliably.
        # So here we enumerate the pumps explicitly instead
        last_pump = 0
        for pump_num, address in PUMP_ADDRESS.items():
            await self._write_async(f"{address}UR\r".encode("ascii"))
            if "NV01" in await self._read_reply_async():
                last_pump = pump_num
            else:
                break
        logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
        return int(last_pump)

    async def _read_reply_async(self) -> str:
        """Read the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.info(f"Reply received: {reply_string}")
        logger.info(f"decode: {reply_string.decode('utf-8')}")
        return reply_string.decode("ascii")




class VersaPump6(FlowchemDevice):
    """ML600 implementation according to manufacturer docs. Tested on a 61501-01 (i.e. single syringe system).

    From manufacturer docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """

    DEFAULT_CONFIG = {
        "default_infuse_rate": "1 ml/min",
        "default_withdraw_rate": "1 ml/min",
    }

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances: set[VersaPump6IO] = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy-chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).

    # Minimum and maximum volume possible for the syringe. (Values in ml)
    MIN_SYRINGE_VOLUME = 0.05
    MAX_SYRINGE_VOLUME = 50.0

    def __init__(
        self,
        pump_io: VersaPump6IO,
        syringe_volume: str,
        name: str,
        address: int = 1,
        **config,
    ) -> None:
        """Default constructor, needs an VersaPump6IO object. See from_config() class method for config-based init.

        Args:
        ----
            pump_io: An VersaPump6IO w/ serial connection to the daisy chain w/ target pump.
            syringe_volume: Volume of the syringe used, either a Quantity or number in ml.
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Versa",
            model="VersaPump 6",
        )
        # HamiltonPumpIO
        self.pump_io = pump_io
        VersaPump6._io_instances.add(self.pump_io)  # See above for details.

        # Pump address is the pump sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # Syringe pumps only perform linear movement, and the volume displaced is function of the syringe loaded.
        try:
            self.syringe_volume = ureg.Quantity(syringe_volume)
        except AttributeError as attribute_error:
            logger.error(f"Invalid syringe volume {syringe_volume}!")
            raise InvalidConfigurationError(
                "Invalid syringe volume provided."
                "The syringe volume is a string with units! e.g. '5 ml'"
            ) from attribute_error

        if self.syringe_volume.m_as("ml") < VersaPump6.MIN_SYRINGE_VOLUME or self.syringe_volume.m_as("ml") > VersaPump6.MAX_SYRINGE_VOLUME:
            raise InvalidConfigurationError(
                f"The specified syringe volume ({syringe_volume}) is invalid!\n"
                f"The volume (in ml) has to be between {VersaPump6.MIN_SYRINGE_VOLUME} ml and {VersaPump6.MAX_SYRINGE_VOLUME} ml"
            )

        self._steps_per_ml = ureg.Quantity(f"{48000 / self.syringe_volume} step")
        self._offset_steps = 100  # Steps added to each absolute move command, to decrease wear and tear at volume = 0
        self._max_vol = (48000 - self._offset_steps) * ureg.step / self._steps_per_ml
        logger.warning(f"due to offset steps is {self._offset_steps}. the max_vol : {self._max_vol}")
        # This enables to configure on per-pump basis uncommon parameters
        self.config = VersaPump6.DEFAULT_CONFIG | config

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of HamiltonPumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        pumpio = None
        for obj in VersaPump6._io_instances:
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
            pumpio = VersaPump6IO.from_config(config_for_pumpio)

        return cls(
            pumpio,
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name", ""),
        )



if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM12",
        "address": 1,
        "name": "test1",
        "syringe_volume": 5,
    }
    pump1 = VersaPump6.from_config(**conf)
    #asyncio.run(pump1.initialize_pump())