from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import Samuel_Saraiva
from flowchem.devices.fakedevice.fakedevice_component import FakeComponent

from loguru import logger

class FakeDevice(FlowchemDevice):
    """Our plugins fake device!"""

    def __init__(self, name):
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[Samuel_Saraiva],
            manufacturer="FakeDevice",
            model="Universal testing Actuator",
        )

    async def initialize(self):
        logger.info('FakeDevice devices was succeccfully initialized!')
        self.components.extend([FakeComponent("FakeComponent",self)])

    def send_command(self, command):
        logger.info(command)  # This is in