""" LTF reactors """
from typing import Optional, Mapping

from flowchem.components.stdlib import Component, MappedComponentMixin


class LTF_HTM_ST_3_1(MappedComponentMixin, Component):
    """
    An LTF HTM ST 3 1 reactor.
    """

    def __init__(self, mapping: Optional[Mapping[Component, int]] = None, name: Optional[str] = None):
        super().__init__(name=name)
        if not isinstance(mapping, (type(None), Mapping)):
            raise TypeError(f"Invalid mapping type {type(mapping)} for {repr(self)}.")
        self.mapping = mapping
        self._visualization_shape = "cds"

    def _validate(self, dry_run):
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping. None provided.")
        return super()._validate(dry_run)
