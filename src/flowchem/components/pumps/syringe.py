"""Syringe pump component, two flavours, infuse only, infuse-withdraw."""
from flowchem.components.component_info import ComponentInfo
from flowchem.components.pumps.base_pump import BasePump


class SyringePump(BasePump):
    def get_component_info(self) -> ComponentInfo:
        # Ontology: syringe pump
        self.component_info.owl_subclass_of = (
            "http://purl.obolibrary.org/obo/OBI_0400100"
        )
        return super().get_component_info()
