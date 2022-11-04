"""A test component."""
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class TestComponent(FlowchemComponent):
    def __int__(self, name: str, hw_device: FlowchemDevice):
        """Initialize a TestComponent with the provided endpoints."""
        super().__init__(name, hw_device)
