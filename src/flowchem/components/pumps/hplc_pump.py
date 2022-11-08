"""Syringe pump component, two flavours, infuse only, infuse-withdraw."""
from abc import ABC

from flowchem.components.pumps.base_pump import BasePump
from flowchem.devices.flowchem_device import FlowchemDevice


class HPLCPump(BasePump, ABC):
    def __int__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)

        # Ontology: HPLC isocratic pump
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/OBI_0000556"
