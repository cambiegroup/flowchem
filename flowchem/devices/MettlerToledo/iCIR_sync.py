""" Sync implementation of FlowIR """

import datetime
import time
import warnings
import logging
from typing import List, Optional

from flowchem.analysis.spectrum import IRSpectrum

from asyncua import ua
from asyncua.ua.uaerrors import BadOutOfService, Bad
import asyncua.sync as opcua

from flowchem.devices.MettlerToledo.iCIR_common import iCIR_spectrometer, FlowIRError, ProbeInfo


class FlowIR_Sync(iCIR_spectrometer):
    """
    Object to interact with the iCIR software controlling the FlowIR and ReactIR.
    """

    def __init__(self, client: opcua.Client):
        """
        Initiate connection with OPC UA server.
        check_version() is executed upon init to check status.
        """
        self.log = logging.getLogger(__name__)

        assert isinstance(client, opcua.Client)

        self.opcua = client
        self.probe = None
        self.version = None

        # Initialize and check connection
        self.opcua.connect()
        self.check_version()

    def __del__(self):
        """ Terminate connection on exit """
        self.opcua.disconnect()

    def check_version(self):
        """ Check if iCIR is installed and open and if the version is supported. """
        try:
            self.version = self.opcua.get_node(
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
    def is_iCIR_connected(self) -> bool:
        """ Check connection with instrument """
        return self.opcua.get_node(self.CONNECTION_STATUS).get_value()

    def probe_info(self) -> ProbeInfo:
        """ Return FlowIR probe information """
        probe_info = self.opcua.get_node(self.PROBE_DESCRIPTION).get_value()
        return self.parse_probe_info(probe_info)

    def probe_status(self) -> str:
        """ Returns current probe status """
        return self.opcua.get_node(self.PROBE_STATUS).get_value()

    def is_running(self) -> bool:
        """ Is the probe currently measuring? """
        return self.probe_status() == "Running"

    def last_sample_time(self) -> datetime.datetime:
        """ Returns date/time of latest scan """
        return self.opcua.get_node(self.LAST_SAMPLE_TIME).get_value()

    def sample_count(self) -> Optional[int]:
        """ Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent """
        return self.opcua.get_node(self.SAMPLE_COUNT).get_value()

    @staticmethod
    def _wavenumber_from_spectrum_node(node) -> List[float]:
        """ Gets the X-axis value of a spectrum. This is necessary as they change e.g. with resolution. """
        x_axis = node.get_properties()[0].get_value()
        return x_axis.AxisSteps

    @staticmethod
    def spectrum_from_node(node) -> IRSpectrum:
        """ Given a Spectrum node returns it as IRSpectrum """
        try:
            intensity = node.get_value()
            wavenumber = FlowIR_Sync._wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber, intensity)
        except BadOutOfService:
            return IRSpectrum([], [])

    def last_spectrum_treated(self) -> IRSpectrum:
        """ Returns an IRSpectrum element for the last acquisition """
        return FlowIR_Sync.spectrum_from_node(self.opcua.get_node(self.SPECTRA_TREATED))

    def last_spectrum_raw(self) -> IRSpectrum:
        """ RAW result latest scan """
        return FlowIR_Sync.spectrum_from_node(self.opcua.get_node(self.SPECTRA_RAW))

    def last_spectrum_background(self) -> IRSpectrum:
        """ RAW result latest scan """
        return FlowIR_Sync.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_BACKGROUND)
        )

    def start_experiment(self, template: str, name: str = "Unnamed flowchem exp."):
        template = FlowIR_Sync._normalize_template_name(template)
        if self.is_local() and FlowIR_Sync.is_template_name_valid(template) is False:
            raise FlowIRError(
                f"Cannot start template {template}: name not valid! Check if is in: "
                r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates"
            )
        if self.is_running():
            warnings.warn(
                "I was asked to start an experiment while a current experiment is already running!"
                "I will have to stop that first! Sorry for that :)"
            )
            # Stop running experiment and wait for the spectrometer to be ready
            self.stop_experiment()
            self.wait_until_idle()

        start_xp_nodeid = self.opcua.get_node(self.START_EXPERIMENT).nodeid
        method_parent = self.opcua.get_node(self.METHODS)
        try:
            # Collect_bg does not seem to work in automation, set to false and do not expose in start_experiment()!
            collect_bg = False
            method_parent.call_method(start_xp_nodeid, name, template, collect_bg)
        except Bad as e:
            raise FlowIRError(
                "The experiment could not be started!"
                "Check iCIR status and close any open experiment."
            ) from e

    def stop_experiment(self):
        """ Stops the experiment currently running (it does not imply instrument is then idle, wait for scan end) """
        method_parent = self.opcua.get_node(self.METHODS)
        stop_nodeid = self.opcua.get_node(self.STOP_EXPERIMENT).nodeid
        method_parent.call_method(stop_nodeid)

    def wait_until_idle(self):
        """ Waits until no experiment is running. """
        while self.is_running:
            time.sleep(0.2)


if __name__ == "__main__":
    opcua_client = opcua.Client(
        url=FlowIR_Sync.iC_OPCUA_DEFAULT_SERVER_ADDRESS.replace("localhost", "BSMC-YMEF002121"),
        timeout=10
    )
    ir_spectrometer = FlowIR_Sync(opcua_client)
    if ir_spectrometer.is_iCIR_connected():
        print("FlowIR connected!")
    else:
        raise ConnectionError("FlowIR not connected :(")

    template_name = "15_sec_integration.iCIRTemplate"
    ir_spectrometer.start_experiment(name="reaction_monitoring", template=template_name)

    spectrum = ir_spectrometer.last_spectrum_treated()
    while spectrum.empty:
        spectrum = ir_spectrometer.last_spectrum_treated()

    for x in range(3):
        spectra_count = ir_spectrometer.sample_count()

        while ir_spectrometer.sample_count() == spectra_count:
            time.sleep(1)

        print("New spectrum!")
        spectrum = ir_spectrometer.last_spectrum_treated()
        print(spectrum)

    ir_spectrometer.stop_experiment()
