""" LTF reactors """
from typing import Optional

from flowchem.components.stdlib import Component, MappedComponentMixin


class LTF_HTM_ST_3_1(MappedComponentMixin, Component):
    """
    An LTF HTM ST 3 1 reactor.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self.mapping = {
            "INLET_1": None,
            "INLET_2": None,
            "QUENCHER": None,
            "OUTLET": None
        }
        self._visualization_shape = "cds"

    def _validate(self, dry_run):
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping. None provided.")
        return super()._validate(dry_run)
