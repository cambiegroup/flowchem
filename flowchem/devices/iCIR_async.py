import datetime
import warnings
from pathlib import Path
from typing import List, Optional
#
# from opcua import Client
# from opcua import ua
# import logging
#
# from opcua.ua.uaerrors import BadOutOfService
import asyncio
from threading import Thread, Condition
import logging
from typing import List, Tuple, Union

from async_property import async_property, async_cached_property
from asyncua import ua
from asyncua import Client
from asyncua import server
from asyncua import common
from asyncua.common import node, subscription, shortcuts, xmlexporter, type_dictionary_builder
from asyncua.ua.uaerrors import BadOutOfService, Bad

logger = logging.getLogger(__name__)


class FlowIRError(Exception):
    pass

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
    def __init__(self, client: Client):
        """ Initiate connection with OPC UA server """
        self.log = logging.getLogger(__name__)

        self.opcua = client
        self.probe = None

    def acquire_background(self):
        pass

    async def get_iC_software_version(self):
        """ Returns iC IR software version or raise FlowIRError """
        try:
            return await self.opcua.get_node("ns=2;s=Local.iCIR.SoftwareVersion").get_value()  # "7.1.91.0"
        except ua.UaStatusCodeError as e:  # iCIR app closed
            raise FlowIRError("iCIR app is closed, cannot control instrument!") from e

    async def is_instrument_connected(self) -> bool:
        """ Check connection with instrument """
        return await self.opcua.get_node("ns=2;s=Local.iCIR.ConnectionStatus").get_value()

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

    async def probe_description(self, probe_num: int = 1):
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

    async def is_running(self):
        """ Is probe 1 is measuring? """
        node = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.ProbeStatus")
        status = await node.get_value()

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

    @async_property
    async def resolution(self):
        """ Returns resolution of probe 1 in cm^(-1) """
        if self.probe is None:
            await self.probe_description()
        return self.probe["resolution"]

    @async_cached_property
    async def detector(self):
        """ Returns detector type """
        if self.probe is None:
            await self.probe_description()
        return self.probe["detector"]

    def acquire_spectrum(self, template: str):
        pass

    def trigger_collection(self):
        pass

    async def get_last_spectrum_treated(self):
        try:
            spectrum = await self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.SpectraTreated").get_value()
        except BadOutOfService:
            spectrum = []
        return spectrum

    async def start_experiment(self, template: str, name: str = "Unnamed flowchem exp.", collect_bg: bool = False):
        if await self.is_running():
            warnings.warn("I was asked to start an experiment while a current experiment is already running!"
                          "I will have to stop that first! Sorry for that :)")
            await self.stop_experiment()
            # And wait for ready...
            while await self.is_running():
                asyncio.sleep(1)

        start_xp_nodeid = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods.Start Experiment").nodeid
        method_parent = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods")
        await method_parent.call_method(start_xp_nodeid, name, template, collect_bg)

    async def stop_experiment(self):
        method_parent = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods")
        stop_nodeid = self.opcua.get_node("ns=2;s=Local.iCIR.Probe1.Methods.Stop").nodeid
        await method_parent.call_method(stop_nodeid)

async def main():
    iC_OPCUA_SERVER_ADDRESS = "opc.tcp://localhost:62552/iCOpcUaServer"

    async with Client(url=iC_OPCUA_SERVER_ADDRESS) as opcua_client:
        ir_spectrometer = FlowIR(opcua_client)
        print(await ir_spectrometer.get_iC_software_version())

        if await ir_spectrometer.is_instrument_connected():
            print(f"FlowIR connected! [Detector type: {await ir_spectrometer.detector}]")
        else:
            print("FlowIR not connected :(")

        print(f"Current resolution set to {await ir_spectrometer.resolution} cm-1")

        # Last spectrum empty before starting an experiment
        spectrum = await ir_spectrometer.get_last_spectrum_treated()
        print(f"Received spectrum is {spectrum}")  # Should be empty

        template_name = "test.iCIRTemplate"
        assert ir_spectrometer.is_template_name_valid(template_name)
        await ir_spectrometer.start_experiment(name="test", template=template_name)

        spectrum = await ir_spectrometer.get_last_spectrum_treated()
        while spectrum == []:
            spectrum = await ir_spectrometer.get_last_spectrum_treated()
        print(spectrum)



if __name__ == '__main__':
    asyncio.run(main())
