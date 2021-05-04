import datetime
import warnings
import logging
from typing import List, Optional

from flowchem.constants.spectrum import IRSpectrum

# ASYNC ONLY
import asyncio
import asyncua
import asyncua.ua.uaerrors
from async_property import async_property
from asyncua import ua
from asyncua.ua.uaerrors import BadOutOfService, Bad

from flowchem.devices.MettlerToledo.base_iCIR import iCIR_spectrometer, IRSpectrometerError, ProbeInfo


class FlowIRError(IRSpectrometerError):
    pass


class FlowIR(iCIR_spectrometer):
    def __init__(self, client: asyncua.Client):
        """
        Initiate connection with OPC UA server.
        Please run check_version() after init to check status (cannot have async call in init).
        """
        self.log = logging.getLogger(__name__)

        assert isinstance(client, asyncua.Client)

        self.opcua = client
        self.probe = None
        self.version = None

    async def check_version(self):
        """ Check if iCIR is installed and open and if the version is supported. """
        try:
            self.version = await self.opcua.get_node(self.SOFTWARE_VERSION).get_value()  # "7.1.91.0"
            if self.version not in FlowIR._supported_versions:
                warnings.warn(f"The current version of iCIR [self.version] has not been tested!"
                              f"Pleas use one of the supported versions: {FlowIR._supported_versions}")
        except ua.UaStatusCodeError as e:  # iCIR app closed
            raise FlowIRError("iCIR app not installed or closed or no instrument available!") from e

    def acquire_background(self):
        raise NotImplementedError

    def acquire_spectrum(self, template: str):
        raise NotImplementedError

    def trigger_collection(self):
        raise NotImplementedError

    @async_property
    async def is_iCIR_connected(self) -> bool:
        """ Check connection with instrument """
        return await self.opcua.get_node(self.CONNECTION_STATUS).get_value()

    @property
    async def probe_info(self) -> ProbeInfo:
        """ Return FlowIR probe information """
        probe_info = await self.opcua.get_node(self.PROBE_DESCRIPTION).get_value()
        return self.parse_probe_info(probe_info)

    @async_property
    async def probe_status(self):
        return await self.opcua.get_node(self.PROBE_STATUS).get_value()

    @async_property
    async def is_running(self) -> bool:
        """ Is the probe currently measuring? """
        return await self.probe_status == "Running"

    async def get_last_sample_time(self) -> datetime.datetime:
        """ Returns date/time of latest scan """
        return await self.opcua.get_node(self.LAST_SAMPLE_TIME).get_value()

    async def get_sample_count(self) -> Optional[int]:
        """ Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent """
        return await self.opcua.get_node(self.SAMPLE_COUNT).get_value()

    @staticmethod
    async def _get_wavenumber_from_spectrum_node(node) -> List[float]:
        """ Gets the X-axis value of a spectrum. This is necessary as they change e.g. with resolution. """
        node_property = await node.get_properties()
        x_axis = await node_property[0].get_value()
        return x_axis.AxisSteps

    @staticmethod
    async def get_spectrum_from_node(node) -> IRSpectrum:
        try:
            intensity = await node.get_value()
            wavenumber = await FlowIR._get_wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber, intensity)

        except BadOutOfService:
            return IRSpectrum([], [])

    async def get_last_spectrum_treated(self) -> IRSpectrum:
        """ Returns an IRSpectrum element for the last acquisition """
        return await FlowIR.get_spectrum_from_node(self.opcua.get_node(self.SPECTRA_TREATED))

    async def get_last_spectrum_raw(self) -> IRSpectrum:
        """ RAW result latest scan """
        return await FlowIR.get_spectrum_from_node(self.opcua.get_node(self.SPECTRA_RAW))

    async def get_last_spectrum_background(self) -> IRSpectrum:
        """ RAW result latest scan """
        return await FlowIR.get_spectrum_from_node(self.opcua.get_node(self.SPECTRA_BACKGROUND))

    async def start_experiment(self, template: str, name: str = "Unnamed flowchem exp."):
        template = FlowIR._normalize_template_name(template)
        if FlowIR.is_template_name_valid(template) is False:
            raise FlowIRError(f"Cannot start template {template}: name not valid! Check if is in: "
                              r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates")
        if await self.is_running:
            warnings.warn("I was asked to start an experiment while a current experiment is already running!"
                          "I will have to stop that first! Sorry for that :)")
            await self.stop_experiment()
            # And wait for ready...
            while await self.is_running:
                await asyncio.sleep(1)

        start_xp_nodeid = self.opcua.get_node(self.START_EXPERIMENT).nodeid
        method_parent = self.opcua.get_node(self.METHODS)
        try:
            collect_bg = False  # This parameter does not work properly so it is not exposed in the method signature
            await method_parent.call_method(start_xp_nodeid, name, template, collect_bg)
        except Bad as e:
            raise FlowIRError("The experiment could not be started!"
                              "Check iCIR status and close any open experiment.") from e

    async def stop_experiment(self):
        method_parent = self.opcua.get_node(self.METHODS)
        stop_nodeid = self.opcua.get_node(self.STOP_EXPERIMENT).nodeid
        await method_parent.call_method(stop_nodeid)


async def main():
    async with asyncua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS) as opcua_client:
        ir_spectrometer = FlowIR(opcua_client)
        await ir_spectrometer.check_version()

        if await ir_spectrometer.is_iCIR_connected:
            print(f"FlowIR connected!")
        else:
            print("FlowIR not connected :(")
            import sys
            sys.exit()

        template_name = "15_sec_integration.iCIRTemplate"
        await ir_spectrometer.start_experiment(name="reaction_monitoring", template=template_name)

        spectrum = await ir_spectrometer.get_last_spectrum_treated()
        while spectrum.empty:
            spectrum = await ir_spectrometer.get_last_spectrum_treated()

        for x in range(3):
            spectra_count = await ir_spectrometer.get_sample_count()

            while await ir_spectrometer.get_sample_count() == spectra_count:
                await asyncio.sleep(1)

            print(f"New spectrum!")
            spectrum = await ir_spectrometer.get_last_spectrum_treated()
            print(spectrum)

        await ir_spectrometer.stop_experiment()


if __name__ == '__main__':
    asyncio.run(main())
