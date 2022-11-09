"""Sensor device."""
from __future__ import annotations

from abc import ABC

from flowchem.components.base_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class Sensor(FlowchemComponent, ABC):
    """A generic sensor."""

    def __int__(self, name: str, hw_device: FlowchemDevice):
        super().__init__(name, hw_device)
        # Ontology: HPLC isocratic pump
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/NCIT_C50166"
