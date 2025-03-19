from .manson_power_supply import MansonPowerSupply
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg


class VirtualMansonPowerSupply(MansonPowerSupply):

    @classmethod
    def from_config(cls, port, name="", **serial_kwargs):
        asw = cls(port, name)
        asw.device_info.authors = [samuel_saraiva]
        asw.device_info.manufacturer = "Virtual Manson"
        asw.device_info.model = "Virtual"

        asw._voltage = 0.0
        asw._current = 0.0
        return asw

    async def get_info(self) -> str:
        return "HCS-3102"

    async def set_current(self, current: str) -> bool:
        self._current = ureg.Quantity(current).magnitude
        return True

    async def set_voltage(self, voltage: str) -> bool:
        self._voltage = ureg.Quantity(voltage).magnitude
        return True

    async def get_output_current(self) -> float:
        return self._current

    async def get_output_voltage(self) -> float:
        return self._voltage

    async def output_on(self) -> bool:
        return True

    async def output_off(self) -> bool:
        return True
