from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem.devices.fakedevice.fakeassemble_components import FakePump, FakeValvePosition, FakeValveDistribution, FakePressureSensor

from loguru import logger

class FakeAssemble(FlowchemDevice):

    device_info = DeviceInfo(
        authors=[samuel_saraiva],
        maintainers=[samuel_saraiva],
        manufacturer="FakeAssemble",
        model="FakeAssemble",
        serial_number=42,
        version="v1.0",
    )

    def __init__(self, name, attribute: str = "communication"):
        super().__init__(name)
        self.communication_attribute = attribute
        self.raw_position = {
            "distribution":"5",
            "position":"2"
        }

    async def initialize(self):
        logger.info('FakeDevice devices was successfully initialized!')
        self.components.extend([FakePump("pump", self)])
        self.components.extend([FakeValvePosition("valve_p", self)])
        self.components.extend([FakeValveDistribution("valve_d", self)])
        self.components.extend([FakePressureSensor("sensor", self)])

    async def set_raw_position(self, target_pos, target_component: str = "distribution"):
        self.raw_position[target_component] = target_pos

    async def get_raw_position(self, target_component: str = "distribution"):
        return self.raw_position[target_component]


if __name__ == '__main__':
    import asyncio

    device = FakeAssemble(name='Fake')
    asyncio.run(device.initialize())
