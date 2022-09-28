"""Syringe pump."""
from abc import ABC

from flowchem.models.pumps.base_pump import BasePump


class SyringePump(BasePump, ABC):
    """A generic Syringe pump."""

    def __init__(self, *args, **kwargs):
        """Add ontology class and call pump constructor."""
        super().__init__(*args, **kwargs)
        # Syringe pump
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0400100")
