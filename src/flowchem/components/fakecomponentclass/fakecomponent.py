"""Base FakeComponent."""
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class FakeComponent(FlowchemComponent):
    def __init__(self, name: str, hw_device: FlowchemDevice, api_parent_method) -> None:
        """A generic FakeComponent."""
        super().__init__(name, hw_device, api_parent_method=api_parent_method)

        #self.add_api_route("/fake_send_command", self.fake_send_command, methods=["PUT"])
        #self.add_api_route("/fake_receive_data", self.fake_receive_data, methods=["GET"])
        self.component_info.type = "FakeComponent"

    async def fake_send_command(self, parameter_1: str = "", parameter_2: str = "") -> bool:
        """
        Send a specific command to the some - FakeDevice.

        This function demonstrates how the commands can be sent through the API build

                Parameters:
                        parameter_1 (str): Some string
                        parameter_2 (str): Some string

                Returns:
                        status (bool): If everything works appropriately the function will return a True
        """
        ...

    async def fake_receive_data(self) -> float:  # type: ignore
        """
        Receive specific data from the FakeDevice.

        This function demonstrates how the commands request of data can be sent through the API build
        """
        ...

    async def fake_not_overwriting_method(self) -> bool:
        """
        A fake method that is not overwritten in the main class's component,
        but only exists in the parent of the component class. This method
        does not interact with hardware; it solely aids in the logic of
        the component's automation.

        Returns:
            bool: Indicates the success or state of the method.
        """
        return True


