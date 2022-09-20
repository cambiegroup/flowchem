from abc import ABC

from flowchem.models.base_device import BaseDevice


class TempControl(BaseDevice, ABC):
    """A generic temperature controller."""

    pass
