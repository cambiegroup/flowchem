from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import Samuel_Saraiva
from flowchem.devices.virtual.chronology_component import Chronology_Component

from io import BytesIO
from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flowchem.server.core import Flowchem

class Chronology(FlowchemDevice):

    device_info = DeviceInfo(
        authors=[Samuel_Saraiva],
        maintainers=[Samuel_Saraiva],
        manufacturer="Vitual Device",
        model="None",
        serial_number=1,
        version="v1.0",
    )

    def __init__(self, name):
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[Samuel_Saraiva],
            manufacturer="Vitual Device",
            model="recording the chronology of events - all devices",
        )

        self.flowchem: Flowchem

        self.config_inf: BytesIO | Path

    async def initialize(self):
        self.components.extend([Chronology_Component("ChronologyComponent",self)])

    def get_flowchem_infor(self, flowchem, config):

        self.flowchem = flowchem

        self.config_inf = config




