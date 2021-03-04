import datetime
from pathlib import Path
from typing import List, Optional

from opcua import Client
from opcua import ua
import logging

from opcua.ua.uaerrors import BadOutOfService

LOG = logging.getLogger("flow-ir")
LOG.setLevel(logging.DEBUG)
LOG.addHandler(logging.StreamHandler())


class SubHandler(object):

    """
    Subscription Handler. To receive events from server for a subscription
    data_change and event methods are called directly from receiving thread.
    Do not do expensive, slow or network operation there. Create another
    thread if you need to do such a thing
    """

    def datachange_notification(self, node, val, data):
        print("Python: New data change event", node, val)

    def event_notification(self, event):
        print("Python: New event", event)


class FlowIR:
    # This is unlikely to change but let's keep it highly visible here just in case ;)
    iC_OPCUA_SERVER_ADDRESS = "opc.tcp://localhost:62552/iCOpcUaServer"

    def __init__(self):
        """ Initiate connection with OPC UA server """
        self.log = logging.getLogger("flow-ir")

        self.opcua = Client(self.iC_OPCUA_SERVER_ADDRESS)
        self.probe = None

        try:
            self.opcua.connect()
            server_name = self.opcua.get_node("ns=2;s=Local.iCIR").get_display_name().Text
            self.log.info(f"Connected to {server_name}")
        except (ConnectionRefusedError, ua.UaStatusCodeError):
            self.opcua = None

    def __del__(self):
        """ Ensure disconnection on object destruction """
        if self.opcua is not False:
            self.opcua.disconnect()

    def acquire_background(self):
        pass

    def get_iC_software_version(self):
        """ Returns iC IR software version or False """
        if self.opcua is None:
            return False

        try:
            version = self.opcua.get_node("ns=2;s=Local.iCIR.SoftwareVersion").get_value()  # "7.1.91.0"
            return version
        except ua.UaStatusCodeError:
            return False

    def is_instrument_connected(self) -> bool:
        """ Check connection with instrument """
        if self.opcua is None:
            return False

        connection_status = self.opcua.get_node("ns=2;s=Local.iCIR.ConnectionStatus").get_value()
        return connection_status  # Avoid return with one liner as it bumpers debug

    def is_template_name_valid(self, template_name: str) -> bool:
        """
        From Mettler Toledo docs:
        You can use the Start method to create and run a new experiment in one of the iC analytical applications
        (i.e. iC IR, iC FBRM, iC Vision, iC Raman). Note that you must provide the name of an existing experiment
        template file that can be used as a basis for the new experiment.
        The template file must be located in a specific folder on the iC OPC UA Server computer.
        This is usually C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates.
        """

        template_directory = Path(r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates")
        if template_directory.exists() and template_directory.is_dir():
            for existing_template in template_directory.glob('*.iCIRTemplate'):
                # Note that I take the filename without extension for this name comparison!
                if existing_template.name == template_name:
                    return True
        return False

    def probe_description(self, probe_num: int = 1):
        """ Return FlowIR probe information """
        if self.opcua is None:
            return False

        probe_info = ir_spectrometer.opcua.get_node(f"ns=2;s=Local.iCIR.Probe{probe_num}.ProbeDescription").get_value()
        # 'FlowIR; SN: 2989; Detector: DTGS; Apodization: HappGenzel; IP Address: 192.168.1.2;
        # Probe: DiComp (Diamond); SN: 14570173; Interface: FlowIR™ Sensor; Sampling: 4000 to 650 cm-1;
        # Resolution: 8; Scan option: AutoSelect; Gain: 232;'
        fields = probe_info.split(";")
        probe_info = {
            "spectrometer": fields[0],
            "spectrometer SN": fields[1].split(": ")[1],
            "probe SN": fields[6].split(": ")[1]
        }

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

    def is_running(self):
        """ Is probe 1 is measuring? """
        if self.opcua is None:
            return False

        status = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.ProbeStatus").get_value()

        if status == "Running":
            return True
        elif status in ("Not running", "Ready"):
            return False
        else:
            self.log.warning(f"Unknown status {status} -- assuming not running...")
            return True

    def get_latest_raw(self) -> List[float]:
        """ RAW result latest scan """
        if self.opcua is None:
            return []

        raw = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SpectraRaw").get_value()
        return raw

    def get_latest_time(self) -> datetime.datetime:
        """ Returns date/time of latest scan """
        # ir_spectrometer.opcua.get_node("ns=2;s=Local.iCIR.Probe1.LastSampleTime").get_value()
        # datetime.datetime(2020, 12, 7, 19, 54, 38)

    def get_sample_count(self) -> Optional[int]:
        """ Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent """
        # ir_spectrometer.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SampleCount").get_value()
        # 6


    @property
    def resolution(self):
        """ Returns resolution of probe 1 in cm^(-1) """
        if self.probe is None and self.probe_description() is False:
            return False
        return self.probe["resolution"]

    def acquire_spectrum(self, template: str):
        pass

    def trigger_collection(self):
        pass

    def get_last_spectrum_treated(self):
        try:
            spectrum = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SpectraTreated").get_value()
        except BadOutOfService:
            spectrum = []
        return spectrum



if __name__ == '__main__':
    ir_spectrometer = FlowIR()
    ir_spectrometer.is_instrument_connected()
    print(ir_spectrometer.get_iC_software_version())
    assert ir_spectrometer.is_template_name_valid("test.iCIRTemplate")
    # assert ir_spectrometer.resolution == 8
    print(ir_spectrometer.get_last_spectrum_treated())

    xp_nid = ir_spectrometer.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods.Start Experiment").nodeid
    xp_nid = ir_spectrometer.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods").call_method(xp_nid, "blabal", "test.iCIRTemplate", False)


