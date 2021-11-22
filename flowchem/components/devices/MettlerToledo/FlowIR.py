""" Async implementation of FlowIR """

import datetime
import warnings
from loguru import logger
from typing import List, Optional

from flowchem.exceptions import DeviceError

import asyncio
from asyncua import ua

from flowchem.components.devices.MettlerToledo.iCIR_common import (
    IRSpectrum,
    iCIR_spectrometer,
    ProbeInfo,
)


class FlowIR(iCIR_spectrometer):
    """
    Object to interact with the iCIR software controlling the FlowIR and ReactIR.
    """

    def __init__(self, url: str = None):
        """
        Initiate connection with OPC UA server.
        Intended to be used as context-manager!
        """
        # Default (local) url if none provided
        if url is None:
            url = "opc.tcp://localhost:62552/iCOpcUaServer"

        self.opcua = asyncua.Client(url)
        self.version = None

    async def initialize(self):
        """Initialize and check connection"""
        try:
            await self.opcua.connect()
        except asyncio.TimeoutError:
            raise DeviceError(
                f"Could not connect to FlowIR on {self.opcua.server_url}!"
            )
        await self.check_version()
        logger.debug("FlowIR initialized!")

    async def check_version(self):
        """Check if iCIR is installed and open and if the version is supported."""
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
            raise DeviceError(
                "iCIR app not installed or closed or no instrument available!"
            ) from e

    # noinspection PyPep8Naming
    async def is_iCIR_connected(self) -> bool:
        """Check connection with instrument"""
        return await self.opcua.get_node(self.CONNECTION_STATUS).get_value()

    async def probe_info(self) -> ProbeInfo:
        """Return FlowIR probe information"""
        probe_info = await self.opcua.get_node(self.PROBE_DESCRIPTION).get_value()
        return self.parse_probe_info(probe_info)

    async def probe_status(self):
        """Returns current probe status"""
        return await self.opcua.get_node(self.PROBE_STATUS).get_value()

    async def is_running(self) -> bool:
        """Is the probe currently measuring?"""
        return await self.probe_status() == "Running"

    async def last_sample_time(self) -> datetime.datetime:
        """Returns date/time of latest scan"""
        return await self.opcua.get_node(self.LAST_SAMPLE_TIME).get_value()

    async def sample_count(self) -> Optional[int]:
        """Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent"""
        return await self.opcua.get_node(self.SAMPLE_COUNT).get_value()

    @staticmethod
    async def _wavenumber_from_spectrum_node(node) -> List[float]:
        """Gets the X-axis value of a spectrum. This is necessary as they change e.g. with resolution."""
        node_property = await node.get_properties()
        x_axis = await node_property[0].get_value()
        return x_axis.AxisSteps

    @staticmethod
    async def spectrum_from_node(node) -> IRSpectrum:
        """Given a Spectrum node returns it as IRSpectrum"""
        try:
            intensity = await node.get_value()
            wavenumber = await FlowIR._wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber=wavenumber, intensity=intensity)

        except ua.uaerrors.BadOutOfService:
            return IRSpectrum(wavenumber=[], intensity=[])

    async def last_spectrum_treated(self) -> IRSpectrum:
        """Returns an IRSpectrum element for the last acquisition"""
        return await FlowIR.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_TREATED)
        )

    async def last_spectrum_raw(self) -> IRSpectrum:
        """RAW result latest scan"""
        return await FlowIR.spectrum_from_node(self.opcua.get_node(self.SPECTRA_RAW))

    async def last_spectrum_background(self) -> IRSpectrum:
        """RAW result latest scan"""
        return await FlowIR.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_BACKGROUND)
        )

    async def start_experiment(
        self, template: str, name: str = "Unnamed flowchem exp."
    ):
        """Starts an experiment on iCIR

        Args:
            template: name of the experiment template, should be in the right folder on the PC running iCIR
            name: experiment name.
        """
        template = FlowIR._normalize_template_name(template)
        if self.is_local() and FlowIR.is_template_name_valid(template) is False:
            raise DeviceError(
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
        except ua.uaerrors.Bad as e:
            raise DeviceError(
                "The experiment could not be started!\n"
                "Check iCIR status and close any open experiment."
            ) from e
        logger.info(f"FlowIR experiment {name} started with template {template}!")

    async def stop_experiment(self):
        """Stops the experiment currently running (it does not imply instrument is then idle, wait for scan end)"""
        method_parent = self.opcua.get_node(self.METHODS)
        stop_nodeid = self.opcua.get_node(self.STOP_EXPERIMENT).nodeid
        await method_parent.call_method(stop_nodeid)

    async def wait_until_idle(self):
        """Waits until no experiment is running."""
        while await self.is_running():
            await asyncio.sleep(0.2)

    def get_router(self):
        """Creates an APIRouter for this HuberChiller instance."""
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/is-connected", self.is_iCIR_connected, methods=["GET"])
        router.add_api_route("/is-running", self.is_running, methods=["GET"])
        router.add_api_route("/probe/info", self.is_iCIR_connected, methods=["GET"])
        router.add_api_route("/probe/status", self.is_iCIR_connected, methods=["GET"])
        router.add_api_route(
            "/sample/last-acquisition-time", self.last_sample_time, methods=["GET"]
        )
        router.add_api_route(
            "/sample/spectrum/last-treated", self.last_spectrum_treated, methods=["GET"]
        )
        router.add_api_route(
            "/sample/spectrum/last-raw", self.last_spectrum_raw, methods=["GET"]
        )
        router.add_api_route(
            "/sample/spectrum/last-background",
            self.last_spectrum_background,
            methods=["GET"],
        )
        router.add_api_route(
            "/experiment/start", self.start_experiment, methods=["PUT"]
        )
        router.add_api_route("/experiment/stop", self.stop_experiment, methods=["GET"])

        return router


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
    #         while len(spectrum.intensity) == 0:
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
