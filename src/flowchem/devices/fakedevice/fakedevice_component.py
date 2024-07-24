from flowchem.components.fakecomponentclass.fakecomponent import FakeComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem import ureg

class pluginpump(FakeComponent):

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)


    async def fake_send_command(self, parameter_1: str = "", parameter_2: str = "") -> bool:  # type: ignore
        """
        Send a specific command to the FakeDevice.

        This function demonstrates how the commands can be sent through the API build

                Parameters:
                        parameter_1 (str): Some string
                        parameter_2 (str): Some string

                Returns:
                        status (bool): If everything works appropriately the function will return a True
        """

        self.hw_device.send_command(f'Send a command to the FakeDevice with parameter_1: {parameter_1} and '
                                    f'parameter_1: {parameter_2}')
        return True # If everything works appropriately the function will return a True

    async def fake_receive_data(self) -> float:  # type: ignore
        """
        Receive specific data from the FakeDevice.

        This function demonstrates how the commands request of data can be sent through the API build
        """
        self.hw_device.send_command(f'Request a data from the FakeDevice')
        return 0.5 # Generic data to show how it works