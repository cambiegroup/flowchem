"""Syringe pump component, two flavours, infuse only, infuse-withdraw."""
from abc import ABC

from loguru import logger

from flowchem.components.pumps.base_pump import BasePump
from flowchem.devices.flowchem_device import FlowchemDevice


class HPLCPump(BasePump, ABC):
    def __int__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""

        logger.error(f"HPLC CALLED")
        super().__init__(name, hw_device)
        logger.error(f"HPLC DONE")
        logger.debug(f"router is {self.router.routes}")

        # Ontology: HPLC isocratic pump
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/OBI_0000556"
