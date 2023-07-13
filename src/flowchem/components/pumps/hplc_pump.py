"""Syringe pump component, two flavours, infuse only, infuse-withdraw."""

from flowchem.components.pumps.pump import Pump
from flowchem.devices.flowchem_device import FlowchemDevice


class HPLCPump(Pump):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)

        # Ontology: HPLC isocratic pump
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0000556",
        )
        self.component_info.type = "HPLC Pump"

    @staticmethod
    def is_withdrawing_capable() -> bool:
        """HPLC pump cannot reverse flow direction (fundamental limit due to displacement + check valves)."""
        return False
