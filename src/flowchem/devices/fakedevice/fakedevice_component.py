from flowchem.components.fakecomponentclass.fakecomponent import FakeComponent
from flowchem.devices.flowchem_device import FlowchemDevice
import time


class FakeComponent_FakeDevice(FakeComponent):

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/set_specif_command", self.set_specif_command, methods=["PUT"])


    async def fake_send_command(self, parameter_1: str = "", parameter_2: str = "") -> bool:  # type: ignore
        """
        This is related to the FakeComponent_FakeDevice from FakeDevice:

                Parameters:
                        parameter_1 (str): in a specific unit (e.g. 3 ml). The value must be within (0 to 40 ml)
                        parameter_2 (str): in a specific unit (e.g. 4 min). The value must be within (0 to 32 min)
        """
        time.sleep(2) # Simulated the delay to run a actuator, for example!

        self.hw_device.send_command(f'Send a command to the FakeDevice with parameter_1: {parameter_1} and '
                                    f'parameter_2: {parameter_2}')
        return True # If everything works appropriately the function will return a True

    async def fake_receive_data(self) -> float:  # type: ignore
        """
        Receive specific data from the FakeDevice.

        This function demonstrates how the commands request of data can be sent through the API build
        """
        self.hw_device.send_command(f'Request a data from the FakeDevice')
        return 0.5 # Generic data to show how it works

    async def set_specif_command(self) -> None:
        """
        This is an example of a specific command that only this device has!

        Returns:
            None
        """
        self.hw_device.send_command(f'Set a specific command')