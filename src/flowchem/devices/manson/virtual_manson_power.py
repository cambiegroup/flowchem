from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.manson.manson_component import MansonPowerControl
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg


class VirtualMansonPowerSupply(FlowchemDevice):

    def __init__(self, name="", **kwargs) -> None:
        """Control class for Manson Power Supply."""
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Manson"
        self.device_info.model = "Virtual"

        self._voltage = 0.0
        self._current = 0.0

    @classmethod
    def from_config(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    async def initialize(self):
        self.components.append(MansonPowerControl("power-control", self)) # typo: ignore

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
