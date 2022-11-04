"""An HPLC control component."""
from abc import ABC

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class HPLCControl(FlowchemComponent, ABC):
    def __int__(self, name: str, hw_device: FlowchemDevice):
        """HPLC Control component. Sends methods, starts run, do stuff."""
        super().__init__(name, hw_device)
        self.add_api_route("/run-sample", self.run_sample, methods=["PUT"])
        self.add_api_route("/send-method", self.send_method, methods=["PUT"])

        # Ontology: high performance liquid chromatography instrument
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/OBI_0001057"

    async def send_method(self, method_name):
        """Submits a method to the HPLC.

        This is e.g. useful when the injection is automatically triggerd when switching a valve.
        """
        ...

    async def run_sample(self, sample_name: str, method_name: str):
        """Runs a sample at the HPLC with the provided sample name and method."""
        ...
