from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import jakob, Samuel_Saraiva, miguel
from flowchem.devices.knauer._common import KnauerEthernetDevice

from flowchem.devices.knauer.knauer_autosampler_component import (
    AutosamplerCNC,
    AutosamplerPump,
    AutosamplerSyringeValve,
    AutosamplerInjectionValve,
)

from loguru import logger

class KnauerAutosampler(FlowchemDevice):
    """Autosampler control class."""
    device_info = DeviceInfo(
        authors=[jakob, Samuel_Saraiva, miguel],
        maintainers=[Samuel_Saraiva],
        manufacturer="Knauer",
        model="Autosampler",
    )

    def __init__(self, name, another_attribute: str = "some_attribute"):
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[jakob, Samuel_Saraiva, miguel],
            maintainers=[Samuel_Saraiva],
            manufacturer="Knauer",
            model="Autosampler",
        )
        self.another_attribute = another_attribute

    async def initialize(self):
        ...


        logger.info('KnauerAutosampler device was successfully initialized!')
        self.components.extend([
            AutosamplerCNC("cnc", self),
            AutosamplerPump("pump", self),
            AutosamplerSyringeValve("syringe_valve", self),
            AutosamplerInjectionValve("injection_valve", self),
        ])


