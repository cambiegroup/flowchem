from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vacuubrand.cvc3000_pressure_control import CVC3000PressureControl
from flowchem.utils.people import samuel_saraiva
from .constants import ProcessStatus
from loguru import logger
import pint


class VirtualCVC3000(FlowchemDevice):

    def __init__(self, name="", **kwargs):
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.version = "Virtual CVC3000"
        self.device_info.manufacturer = "Vitual Device"

    async def initialize(self):
        self.components.append(CVC3000PressureControl("pressure-control", self)) # type: ignore

    @classmethod
    def from_config(cls, *arg, **kwargs):
        return cls(*arg, **kwargs)

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

    async def power_on(self):
        return "1"

    async def power_off(self):
        return "1"
