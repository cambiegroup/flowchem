"""Analytical device."""
from abc import ABC

from flowchem.models.base_device import BaseDevice


class AnalyticalDevice(BaseDevice, ABC):
    """A generic analytical device."""

    def __init__(self, name: str | None = None):
        """Add ontology class and return superclass constructor."""
        super().__init__(name)
        self.owl_subclass_of.add(" http://purl.obolibrary.org/obo/OBI_0000832")

    def get_router(self, prefix: str | None = None):
        """Return APIRouter."""
        return super().get_router(prefix)
