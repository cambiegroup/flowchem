from typing import Optional

from flowchem.components.properties import PassiveComponent


class PassiveMixer(PassiveComponent):
    """
    A generic mixer (essentially an alias of PassiveComponent).
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
