import pint

from flowchem.utils.people import samuel_saraiva
from .constants import ProcessStatus
from .cvc3000 import CVC3000
from loguru import logger


class VirtualCVC3000(CVC3000):

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs):
        aws = cls(port, name)
        aws._pressure = 0
        aws.device_info.authors = [samuel_saraiva]
        return aws

    async def version(self):
        return "VIRTUAL"

    async def _send_command_and_read_reply(self, command: str) -> str:
        logger.debug(f"Command `{command}` to virtual cvc3000 sent!")
        return "0"

    async def set_pressure(self, pressure: pint.Quantity):
        self._pressure = int(pressure.m_as("mbar"))

    async def get_pressure(self):
        return self._pressure

    async def status(self) -> ProcessStatus:
        p = ProcessStatus.from_reply("000002")
        return p
