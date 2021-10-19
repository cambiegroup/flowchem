""" Async implementation of FlowIR """

import datetime
import warnings
import logging
from typing import List, Optional

from flowchem.analysis.spectrum import IRSpectrum

import asyncio
import asyncua.ua.uaerrors
from asyncua import ua
from asyncua.ua.uaerrors import BadOutOfService, Bad

from flowchem.devices.MettlerToledo.iCIR_common import iCIR_spectrometer, FlowIRError, ProbeInfo


class FlowIR_Async(iCIR_spectrometer):
    """
    Object to interact with the iCIR software controlling the FlowIR and ReactIR.
    """

    def __init__(self, client: asyncua.Client):
        """
        Initiate connection with OPC UA server.
        Intended to be used as context-manager!
        """
        self.log = logging.getLogger(__name__)

        assert isinstance(client, asyncua.Client)

        self.opcua = client
        self.probe = None
        self.version = None

    async def __aenter__(self):
        # Initialize and check connection
        await self.opcua.connect()
        await self.check_version()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.opcua.disconnect()

    async def check_version(self):
        """ Check if iCIR is installed and open and if the version is supported. """
        try:
            self.version = await self.opcua.get_node(
                self.SOFTWARE_VERSION
            ).get_value()  # "7.1.91.0"
            if self.version not in self._supported_versions:
                warnings.warn(
                    f"The current version of iCIR [self.version] has not been tested!"
                    f"Pleas use one of the supported versions: {self._supported_versions}"
                )
        except ua.UaStatusCodeError as e:  # iCIR app closed
            raise FlowIRError(
                "iCIR app not installed or closed or no instrument available!"
            ) from e

    # noinspection PyPep8Naming
    async def is_iCIR_connected(self) -> bool:
        """ Check connection with instrument """
        return await self.opcua.get_node(self.CONNECTION_STATUS).get_value()

    async def probe_info(self) -> ProbeInfo:
        """ Return FlowIR probe information """
        probe_info = await self.opcua.get_node(self.PROBE_DESCRIPTION).get_value()
        return self.parse_probe_info(probe_info)

    async def probe_status(self):
        """ Returns current probe status """
        return await self.opcua.get_node(self.PROBE_STATUS).get_value()

    async def is_running(self) -> bool:
        """ Is the probe currently measuring? """
        return await self.probe_status() == "Running"

    async def last_sample_time(self) -> datetime.datetime:
        """ Returns date/time of latest scan """
        return await self.opcua.get_node(self.LAST_SAMPLE_TIME).get_value()

    async def sample_count(self) -> Optional[int]:
        """ Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent """
        return await self.opcua.get_node(self.SAMPLE_COUNT).get_value()

    @staticmethod
    async def _wavenumber_from_spectrum_node(node) -> List[float]:
        """ Gets the X-axis value of a spectrum. This is necessary as they change e.g. with resolution. """
        node_property = await node.get_properties()
        x_axis = await node_property[0].get_value()
        return x_axis.AxisSteps

    @staticmethod
    async def spectrum_from_node(node) -> IRSpectrum:
        """ Given a Spectrum node returns it as IRSpectrum """
        try:
            intensity = await node.get_value()
            wavenumber = await FlowIR_Async._wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber, intensity)

        except BadOutOfService:
            return IRSpectrum([], [])

    async def last_spectrum_treated(self) -> IRSpectrum:
        """ Returns an IRSpectrum element for the last acquisition """
        return await FlowIR_Async.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_TREATED)
        )

    async def last_spectrum_raw(self) -> IRSpectrum:
        """ RAW result latest scan """
        return await FlowIR_Async.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_RAW)
        )

    async def last_spectrum_background(self) -> IRSpectrum:
        """ RAW result latest scan """
        return await FlowIR_Async.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_BACKGROUND)
        )

    async def start_experiment(
        self, template: str, name: str = "Unnamed flowchem exp."
    ):
        template = FlowIR_Async._normalize_template_name(template)
        if self.is_local() and FlowIR_Async.is_template_name_valid(template) is False:
            raise FlowIRError(
                f"Cannot start template {template}: name not valid! Check if is in: "
                r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates"
            )
        if await self.is_running():
            warnings.warn(
                "I was asked to start an experiment while a current experiment is already running!"
                "I will have to stop that first! Sorry for that :)"
            )
            # Stop running experiment and wait for the spectrometer to be ready
            await self.stop_experiment()
            await self.wait_until_idle()

        start_xp_nodeid = self.opcua.get_node(self.START_EXPERIMENT).nodeid
        method_parent = self.opcua.get_node(self.METHODS)
        try:
            # Collect_bg does not seem to work in automation, set to false and do not expose in start_experiment()!
            collect_bg = False
            await method_parent.call_method(start_xp_nodeid, name, template, collect_bg)
        except Bad as e:
            raise FlowIRError(
                "The experiment could not be started!\n"
                "Check iCIR status and close any open experiment."
            ) from e

    async def stop_experiment(self):
        """ Stops the experiment currently running (it does not imply instrument is then idle, wait for scan end) """
        method_parent = self.opcua.get_node(self.METHODS)
        stop_nodeid = self.opcua.get_node(self.STOP_EXPERIMENT).nodeid
        await method_parent.call_method(stop_nodeid)

    async def wait_until_idle(self):
        """ Waits until no experiment is running. """
        while await self.is_running():
            await asyncio.sleep(0.2)


if __name__ == "__main__":
    ...
    # async def main():
    #     opcua_client = asyncua.Client(
    #         url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS.replace("localhost", "BSMC-YMEF002121")
    #     )
    #
    #     async with FlowIR(opcua_client) as ir_spectrometer:
    #         await ir_spectrometer.check_version()
    #
    #         if await ir_spectrometer.is_iCIR_connected():
    #             print("FlowIR connected!")
    #         else:
    #             raise ConnectionError("FlowIR not connected :(")
    #
    #         template_name = "15_sec_integration.iCIRTemplate"
    #         await ir_spectrometer.start_experiment(
    #             name="reaction_monitoring", template=template_name
    #         )
    #
    #         spectrum = await ir_spectrometer.last_spectrum_treated()
    #         while spectrum.empty:
    #             spectrum = await ir_spectrometer.last_spectrum_treated()
    #
    #         for x in range(3):
    #             spectra_count = await ir_spectrometer.sample_count()
    #
    #             while await ir_spectrometer.sample_count() == spectra_count:
    #                 await asyncio.sleep(1)
    #
    #             print("New spectrum!")
    #             spectrum = await ir_spectrometer.last_spectrum_treated()
    #             print(spectrum)
    #
    #         await ir_spectrometer.stop_experiment()
    #
    # asyncio.run(main())
