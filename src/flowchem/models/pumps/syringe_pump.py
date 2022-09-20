from abc import ABC

from flowchem.models.base_device import BaseDevice


class SyringePump(BaseDevice, ABC):
    """A generic Syringe pump."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Syringe pump
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0400100")
