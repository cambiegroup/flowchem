"""Vacuubrand CVC3000 control."""
import asyncio

import aioserial
import pint
from loguru import logger

from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vacuubrand.cvc3000_pressure_control import CVC3000PressureControl
from flowchem.devices.vacuubrand.utils import ProcessStatus
from flowchem.utils.exceptions import InvalidConfiguration
from flowchem.utils.people import dario, jakob, wei_hsin


class CVC3000(FlowchemDevice):
    """Control class for CVC3000."""

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 19200,  # Supports 2400-19200
        "parity": aioserial.PARITY_NONE,  # Other values possible via config
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(
        self,
        aio: aioserial.AioSerial,
        name="",
    ):
        super().__init__(name)
        self._serial = aio
        self._device_sn: int = None  # type: ignore

        self.metadata = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="Vacuubrand",
            model="CVC3000",
        )

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs):
        """
        Create instance from config dict. Used by server to initialize obj from config.

        Only required parameter is 'port'. Optional 'loop' + others (see AioSerial())
        """
        # Merge default settings, including serial, with provided ones.
        configuration = CVC3000.DEFAULT_CONFIG | serial_kwargs

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except (OSError, aioserial.SerialException) as serial_exception:
            raise InvalidConfiguration(
                f"Cannot connect to the CVC3000 on the port <{port}>"
            ) from serial_exception

        return cls(serial_object, name)

    async def initialize(self):
        """Ensure the connection w/ device is working."""
        self.metadata.version = await self.version()
        if not self.metadata.version:
            raise InvalidConfiguration("No reply received from CVC3000!")

        # Set to CVC3000 mode and save
        await self._send_command_and_read_reply("CVC 3")
        await self._send_command_and_read_reply("STORE")
        # Get reply to set commands
        await self._send_command_and_read_reply("ECHO 1")
        # Remote control
        await self._send_command_and_read_reply("REMOTE 1")
        # mbar, no autostart, no beep, venting auto
        await self._send_command_and_read_reply("OUT_CFG 00001")
        await self.motor_speed(100)

        logger.debug(f"Connected with CVC3000 version {self.metadata.version}")

    async def _send_command_and_read_reply(self, command: str) -> str:
        """
        Send command and read the reply.

        Args:
            command (str): string to be transmitted

        Returns:
            str: reply received
        """
        await self._serial.write_async(command.encode("ascii") + b"\r\n")
        logger.debug(f"Command `{command}` sent!")

        # Receive reply and return it after decoding
        try:
            reply = await asyncio.wait_for(self._serial.readline_async(), 2)
        except asyncio.TimeoutError:
            logger.error("No reply received! Unsupported command?")
            return ""

        await asyncio.sleep(0.1)  # Max rate 10 commands/s as per manual

        logger.debug(f"Reply received: {reply}")
        return reply.decode("ascii")

    async def version(self):
        """Get version."""
        raw_version = await self._send_command_and_read_reply("IN_VER")
        # raw_version = CVC 3000 VX.YY
        try:
            return raw_version.split()[-1]
        except IndexError:
            return None

    async def set_pressure(self, pressure: pint.Quantity):
        mbar = int(pressure.m_as("mbar"))
        await self._send_command_and_read_reply(f"OUT_SP_1 {mbar}")

    async def get_pressure(self):
        """Return current pressure in mbar."""
        pressure_text = await self._send_command_and_read_reply("IN_PV_1")
        return float(pressure_text.split()[0])

    async def motor_speed(self, speed):
        """Sets motor speed to target % value."""
        return await self._send_command_and_read_reply(f"OUT_SP_2 {speed}")

    async def status(self) -> ProcessStatus:
        """Get process status reply."""
        raw_status = await self._send_command_and_read_reply("IN_STAT")
        # Sometimes fails on first call
        if not raw_status:
            raw_status = await self._send_command_and_read_reply("IN_STAT")
        return ProcessStatus.from_reply(raw_status)

    def components(self):
        """Return a TemperatureControl component."""
        return (CVC3000PressureControl("pressure-control", self),)
