from flowchem.components.analytics.ir import IRSpectrum
from flowchem.devices.mettlertoledo.icir_control import IcIRControl
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import samuel_saraiva


class VirtualIcIR(FlowchemDevice):

    def __init__(self, name="", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer="Virtual Mettler-Toledo"
        self.device_info.model="Virtual iCIR"
        self.device_info.version=""

    async def initialize(self):
        self.components.append(IcIRControl("ir-control", self)) # type: ignore

    async def last_spectrum_treated(self) -> IRSpectrum:
        return await self.last_spectrum_raw()

    async def last_spectrum_raw(self) -> IRSpectrum:
        asw = IRSpectrum(
            wavenumber=[0],
            intensity=[0]
        )
        return asw

    async def sample_count(self) -> int | None:
        return 0

    async def stop_experiment(self):
        return True



