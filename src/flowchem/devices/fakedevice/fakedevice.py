from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import Samuel_Saraiva
from flowchem.devices.fakedevice.fakedevice_component import FakeComponent_FakeDevice
from loguru import logger

class FakeDeviceExample(FlowchemDevice):
    """Our plugins fake device!"""
    device_info = DeviceInfo(
        authors=[Samuel_Saraiva],
        maintainers=[Samuel_Saraiva],
        manufacturer="Fake-device",
        model="FakeDevice",
        serial_number=42,
        version="v1.0",
    )

    def __init__(self, name):
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[Samuel_Saraiva],
            manufacturer="FakeDeviceExample",
            model="Universal testing Actuator",
        )

    async def initialize(self):
        logger.info('FakeDevice devices was succeccfully initialized!')
        self.components.extend([FakeComponent_FakeDevice("FakeComponent",self)])

    async def send_command(self, command):
        logger.info(command)  # This is in



if __name__ == '__main__':
    import asyncio

    device = FakeDeviceExample(name='Fake')
    asyncio.run(device.initialize())





