import datetime
import warnings
from pathlib import Path
import asyncio
import logging
from typing import List, Optional

import asyncua.ua.uaerrors
from async_property import async_property, async_cached_property
from asyncua import ua
from asyncua import Client
from asyncua.common.structures import load_type_definitions
from asyncua.ua.uaerrors import BadOutOfService

from flowchem.constants.spectrum import IRSpectrum

logger = logging.getLogger(__name__)


class FlowIRError(Exception):
    pass


class FlowIR:
    iC_OPCUA_DEFAULT_SERVER_ADDRESS = "opc.tcp://localhost:62552/iCOpcUaServer"
    _supported_versions = {"7.1.91.0"}

    def __init__(self, client: Client):
        """
        Initiate connection with OPC UA server.
        Please run check_version() after init to check status (cannot have async call in init).
        """
        self.log = logging.getLogger(__name__)

        self.opcua = client
        self.probe = None
        self.version = None

    async def check_version(self):
        """ Check if iCIR is installed and open and if the version is supported. """
        try:
            self.version = await self.opcua.get_node("ns=2;s=Local.iCIR.SoftwareVersion").get_value()  # "7.1.91.0"
            if self.version not in FlowIR._supported_versions:
                warnings.warn(f"The current version of iCIR [self.version] has not been tested!"
                              f"Pleas use one of the supported versions: {FlowIR._supported_versions}")
        except ua.UaStatusCodeError as e:  # iCIR app closed
            raise FlowIRError("iCIR app is closed or not installed!") from e

    def acquire_background(self):
        raise NotImplementedError

    @async_property
    async def is_iCIR_connected(self) -> bool:
        """ Check connection with instrument """
        return await self.opcua.get_node("ns=2;s=Local.iCIR.ConnectionStatus").get_value()

    @staticmethod
    def _normalize_template_name(template_name) -> str:
        """ Adds .iCIRTemplate extension from string if not already present """
        return template_name if template_name.endswith('.iCIRTemplate') else template_name+'.iCIRTemplate'

    @staticmethod
    def is_template_name_valid(template_name: str) -> bool:
        """
        From Mettler Toledo docs:
        You can use the Start method to create and run a new experiment in one of the iC analytical applications
        (i.e. iC IR, iC FBRM, iC Vision, iC Raman). Note that you must provide the name of an existing experiment
        template file that can be used as a basis for the new experiment.
        The template file must be located in a specific folder on the iC OPC UA Server computer.
        This is usually C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates.
        """

        template_directory = Path(r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates")
        if not template_directory.exists() or not template_directory.is_dir():
            raise FlowIRError("iCIR template folder not found!")

        # Ensures the name has been provided with no extension (common mistake)
        template_name = FlowIR._normalize_template_name(template_name)
        for existing_template in template_directory.glob('*.iCIRTemplate'):
            if existing_template.name == template_name:
                return True
        return False

    async def _load_probe_description(self, probe_num: int = 1):
        """ Return FlowIR probe information """
        node = self.opcua.get_node(f"ns=2;s=Local.iCIR.Probe{probe_num}.ProbeDescription")
        probe_info = await node.get_value()
        # 'FlowIR; SN: 2989; Detector: DTGS; Apodization: HappGenzel; IP Address: 192.168.1.2;
        # Probe: DiComp (Diamond); SN: 14570173; Interface: FlowIR™ Sensor; Sampling: 4000 to 650 cm-1;
        # Resolution: 8; Scan option: AutoSelect; Gain: 232;'
        fields = probe_info.split(";")
        probe_info = {
            "spectrometer": fields[0],
            "spectrometer SN": fields[1].split(": ")[1],
            "probe SN": fields[6].split(": ")[1]
        }

        # Use aliases, i.e. translate API names (left) to dict key (right)
        translate_attributes = {
            "Detector": "detector",
            "Apodization": "apodization",
            "IP Address": "ip address",
            "Probe": "probe type",
            "Sampling": "sampling interval",
            "Resolution": "resolution",
            "Scan option": "scan option",
            "Gain": "gain"
        }
        for element in fields:
            if ":" in element:
                piece = element.split(":")
                if piece[0].strip() in translate_attributes:
                    probe_info[translate_attributes[piece[0].strip()]] = piece[1].strip()

        self.probe = probe_info

    @async_property
    async def resolution(self):
        """ Returns resolution of probe 1 in cm^(-1) """
        await self._load_probe_description()
        return self.probe["resolution"]

    @async_cached_property
    async def detector(self):
        """ Returns detector type """
        if self.probe is None:
            await self._load_probe_description()
        return self.probe["detector"]

    @async_property
    async def probe_status(self):
        return await self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.ProbeStatus").get_value()

    @async_property
    async def is_running(self) -> bool:
        """ Is the probe currently measuring? """
        status = await self.probe_status

        if status == "Running":
            return True
        elif status in ("Not running", "Ready"):
            return False
        else:
            self.log.warning(f"Unknown status {status} -- assuming not running...")
            return True

    async def get_last_sample_time(self) -> datetime.datetime:
        """ Returns date/time of latest scan """
        return await self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.LastSampleTime").get_value()

    async def get_sample_count(self) -> Optional[int]:
        """ Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent """
        return await self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SampleCount").get_value()

    def acquire_spectrum(self, template: str):
        pass

    def trigger_collection(self):
        pass

    @staticmethod
    async def _get_wavenumber_from_spectrum_node(node) -> List[float]:
        """  """
        node_property = await node.get_properties()
        x_axis = await node_property[0].read_value()
        return x_axis.AxisSteps

    @staticmethod
    async def get_spectrum_from_node(node) -> IRSpectrum:
        try:
            intensity = await node.read_value()
            wavenumber = await FlowIR._get_wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber, intensity)

        except BadOutOfService:
            return IRSpectrum([], [])

    async def get_last_spectrum_treated(self) -> IRSpectrum:
        """ Returns an IRSpectrum element for the last acquisition """
        return await FlowIR.get_spectrum_from_node(self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SpectraTreated"))

    async def get_last_spectrum_raw(self) -> IRSpectrum:
        """ RAW result latest scan """
        return await FlowIR.get_spectrum_from_node(self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SpectraRaw"))

    async def get_last_spectrum_background(self) -> IRSpectrum:
        """ RAW result latest scan """
        return await FlowIR.get_spectrum_from_node(self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SpectraBackground"))

    async def start_experiment(self, template: str, name: str = "Unnamed flowchem exp.", collect_bg: bool = False):
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

        start_xp_nodeid = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods.Start Experiment").nodeid
        method_parent = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods")
        try:
            await method_parent.call_method(start_xp_nodeid, name, template, collect_bg)
        except asyncua.ua.uaerrors.Bad as e:
            raise FlowIRError("The experiment could not be started!"
                              "Check iCIR status and close any open experiment.") from e

    async def stop_experiment(self):
        method_parent = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods")
        stop_nodeid = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods.Stop").nodeid
        await method_parent.call_method(stop_nodeid)


async def main():
    async with Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS) as opcua_client:
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
