import datetime
import time
import warnings
import logging
from typing import List, Optional

from flowchem.analysis.spectrum import IRSpectrum

# SYNC ONLY
import opcua
from opcua import ua
from opcua.ua.uaerrors import BadOutOfService, Bad

from flowchem.devices.MettlerToledo.base_iCIR import (
    iCIR_spectrometer,
    IRSpectrometerError,
    ProbeInfo,
)


class FlowIRError(IRSpectrometerError):
    pass


class FlowIR(iCIR_spectrometer):
    def __init__(self, client: opcua.Client):
        """
        Initiate connection with OPC UA server.
        check_version() is executed upon init to check status.
        """
        self.log = logging.getLogger(__name__)

        assert isinstance(client, opcua.Client)

        self.opcua = client
        self.opcua.connect()
        self.probe = None
        self.version = None
        self.check_version()

    def check_version(self):
        """ Check if iCIR is installed and open and if the version is supported. """
        try:
            self.version = self.opcua.get_node(
                self.SOFTWARE_VERSION
            ).get_value()  # "7.1.91.0"
            if self.version not in FlowIR._supported_versions:
                warnings.warn(
                    f"The current version of iCIR [self.version] has not been tested!"
                    f"Pleas use one of the supported versions: {FlowIR._supported_versions}"
                )
        except ua.UaStatusCodeError as e:  # iCIR app closed
            raise FlowIRError(
                "iCIR app not installed or closed or no instrument available!"
            ) from e

    def acquire_background(self):
        raise NotImplementedError

    def acquire_spectrum(self, template: str):
        raise NotImplementedError

    def trigger_collection(self):
        raise NotImplementedError

    @property
    def is_iCIR_connected(self) -> bool:
        """ Check connection with instrument """
        return self.opcua.get_node(self.CONNECTION_STATUS).get_value()

    @property
    def probe_info(self) -> ProbeInfo:
        """ Return FlowIR probe information """
        probe_info = self.opcua.get_node(self.PROBE_DESCRIPTION).get_value()
        return self.parse_probe_info(probe_info)

    @property
    def probe_status(self):
        return self.opcua.get_node(self.PROBE_STATUS).get_value()

    @property
    def is_running(self) -> bool:
        """ Is the probe currently measuring? """
        return self.probe_status == "Running"

    def get_last_sample_time(self) -> datetime.datetime:
        """ Returns date/time of latest scan """
        return self.opcua.get_node(self.LAST_SAMPLE_TIME).get_value()

    def get_sample_count(self) -> Optional[int]:
        """ Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent """
        return self.opcua.get_node(self.SAMPLE_COUNT).get_value()

    @staticmethod
    def _get_wavenumber_from_spectrum_node(node) -> List[float]:
        """ Gets the X-axis value of a spectrum. This is necessary as they change e.g. with resolution. """
        x_axis = node.get_properties()[0].get_value()
        return x_axis.AxisSteps

    @staticmethod
    def get_spectrum_from_node(node) -> IRSpectrum:
        try:
            intensity = node.get_value()
            wavenumber = FlowIR._get_wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber, intensity)
        except BadOutOfService:
            return IRSpectrum([], [])

    def get_last_spectrum_treated(self) -> IRSpectrum:
        """ Returns an IRSpectrum element for the last acquisition """
        return FlowIR.get_spectrum_from_node(self.opcua.get_node(self.SPECTRA_TREATED))

    def get_last_spectrum_raw(self) -> IRSpectrum:
        """ RAW result latest scan """
        return FlowIR.get_spectrum_from_node(self.opcua.get_node(self.SPECTRA_RAW))

    def get_last_spectrum_background(self) -> IRSpectrum:
        """ RAW result latest scan """
        return FlowIR.get_spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_BACKGROUND)
        )

    def start_experiment(self, template: str, name: str = "Unnamed flowchem exp."):
        template = FlowIR._normalize_template_name(template)
        if FlowIR.is_template_name_valid(template) is False:
            raise FlowIRError(
                f"Cannot start template {template}: name not valid! Check if is in: "
                r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates"
            )
        if self.is_running:
            warnings.warn(
                "I was asked to start an experiment while a current experiment is already running!"
                "I will have to stop that first! Sorry for that :)"
            )
            self.stop_experiment()
            # And wait for ready...
            while self.is_running:
                time.sleep(1)

        start_xp_nodeid = self.opcua.get_node(self.START_EXPERIMENT).nodeid
        method_parent = self.opcua.get_node(self.METHODS)
        try:
            collect_bg = False  # This parameter does not work properly so it is not exposed in the method signature
            method_parent.call_method(start_xp_nodeid, name, template, collect_bg)
        except Bad as e:
            raise FlowIRError(
                "The experiment could not be started!"
                "Check iCIR status and close any open experiment."
            ) from e

    def stop_experiment(self):
        method_parent = self.opcua.get_node(self.METHODS)
        stop_nodeid = self.opcua.get_node(self.STOP_EXPERIMENT).nodeid
        method_parent.call_method(stop_nodeid)


if __name__ == "__main__":
    client = opcua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS, timeout=10)
    ir_spectrometer = FlowIR(client)
    if ir_spectrometer.is_iCIR_connected:
        print(f"FlowIR connected!")
    else:
        print("FlowIR not connected :(")
        import sys

        sys.exit()

    template_name = "15_sec_integration.iCIRTemplate"
    ir_spectrometer.start_experiment(name="reaction_monitoring", template=template_name)

    spectrum = ir_spectrometer.get_last_spectrum_treated()
    while spectrum.empty:
        spectrum = ir_spectrometer.get_last_spectrum_treated()

    for x in range(3):
        spectra_count = ir_spectrometer.get_sample_count()

        while ir_spectrometer.get_sample_count() == spectra_count:
            time.sleep(1)

        print(f"New spectrum!")
        spectrum = ir_spectrometer.get_last_spectrum_treated()
        print(spectrum)

    ir_spectrometer.stop_experiment()
