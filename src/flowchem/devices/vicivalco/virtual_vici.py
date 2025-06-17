from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vicivalco.vici_valve_component import ViciInjectionValve
from flowchem.utils.people import samuel_saraiva


class VirtualViciValve(FlowchemDevice):

    def __init__(self, name: str = "", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors.append(samuel_saraiva)
        self.device_info.manufacturer="Virtual Phidget"
        self.device_info.model="Virtual BubbleSensor"

        self._position = "1"

    @classmethod
    def from_config(cls, *arg, **kwargs):
        return cls(*arg, **kwargs)

    async def initialize(self):
        # Add component
        self.components.append(ViciInjectionValve("injection-valve", self)) # type: ignore

    async def set_raw_position(self, position: str):
        self._position = position

    async def get_raw_position(self) -> str:
        return self._position




