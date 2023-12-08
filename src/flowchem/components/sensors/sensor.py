"""Sensor device."""
from __future__ import annotations

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class Sensor(FlowchemComponent):
    """A generic sensor."""

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/power-on", self.power_on, methods=["PUT"])
        self.add_api_route("/power-off", self.power_off, methods=["PUT"])
        # Ontology: HPLC isocratic pump
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/NCIT_C50166",
        )

    async def power_on(self):
        """"""
        ...

    async def power_off(self):
        ...
