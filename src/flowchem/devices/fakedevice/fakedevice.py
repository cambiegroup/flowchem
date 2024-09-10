from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import Samuel_Saraiva
from flowchem.devices.fakedevice.fakedevice_component import FakeComponent_FakeDevice
from loguru import logger


class FakeDeviceExample(FlowchemDevice):
    """
    A simulated example of a device class that extends FlowchemDevice. This device is used to demonstrate how
    a plugin can interact with the Flowchem framework. The device is identified by the FakeDevice model and
    includes a single component, FakeComponent_FakeDevice, which is initialized when the device is set up.

    This example shows how to create a custom device within the Flowchem ecosystem, including setting up device
    information, initializing the device, and sending commands to its components.
    """

    # Device metadata
    device_info = DeviceInfo(
        authors=[Samuel_Saraiva],
        maintainers=[Samuel_Saraiva],
        manufacturer="Fake-device",
        model="FakeDevice",
        serial_number=42,
        version="v1.0",
    )

    def __init__(self, name: str, another_attribute: str = "some_attribute"):
        """
        Initializes the FakeDeviceExample instance.

        Args:
            name (str): The name of the device.
            another_attribute (str): An optional attribute for demonstration purposes, defaults to "some_attribute".
        """
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[Samuel_Saraiva],
            manufacturer="FakeDeviceExample",
            model="Universal testing Actuator",
        )
        self.another_attribute = another_attribute

    async def initialize(self):
        """
        Asynchronously initializes the FakeDeviceExample.

        This method sets up the device, adds the `FakeComponent_FakeDevice` component to the device,
        and logs the successful initialization of the device.
        """
        logger.info('FakeDevice device was successfully initialized!')
        self.components.extend([FakeComponent_FakeDevice("FakeComponent", self)])

    async def send_command(self, command: str):
        """
        Logs a command that is sent to the device.

        Args:
            command (str): The command to be sent to the device.
        """
        logger.info(command)


if __name__ == '__main__':
    import asyncio

    device = FakeDeviceExample(name='Fake')
    asyncio.run(device.initialize())
