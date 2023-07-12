"""Syringe pump component, two flavours, infuse only, infuse-withdraw."""
from flowchem.components.pumps.base_pump import BasePump
from flowchem.devices.flowchem_device import FlowchemDevice


class SyringePump(BasePump):
    def __init__(self, name: str, hw_device: FlowchemDevice):
        super().__init__(name, hw_device)

        # Ontology: Syringe pump
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0400100"
        )
        self.component_info.type = "Syringe Pump"
