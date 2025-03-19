from .icir import IcIR, IcIRControl, IRSpectrum
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva


class VirtualIcIR(IcIR):

    def __init__(self, template="", url="", name="") -> None:
        """Initiate connection with OPC UA server."""

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Mettler-Toledo",
            model="Virtual iCIR",
            version="",
        )
        self.name = name
        self.components = []

        self._template = template

    async def initialize(self):
        # Set IRSpectrometer component
        self.components.append(IcIRControl("ir-control", self))

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



