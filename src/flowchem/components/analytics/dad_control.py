"""A Diode Array Detector control component."""
from flowchem.components.base_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class DADControl(FlowchemComponent):
    def __int__(self, name: str, hw_device: FlowchemDevice):
        """DAD Control component."""
        super().__init__(name, hw_device)
        self.add_api_route("/lamp", self.get_lamp, methods=["GET"])
        self.add_api_route("/lamp", self.set_lamp, methods=["PUT"])

        # Ontology: diode array detector
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/CHMO_0002503"

    async def get_lamp(self):
        """Lamp status."""
        ...

    async def set_lamp(self, state: bool, lamp_name: str):
        """Lamp status."""
        ...
