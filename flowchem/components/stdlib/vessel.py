from typing import Optional

from flowchem.components.stdlib import Component


class Vessel(Component):
    """
    A generic vessel.

    Arguments:
    - `description`: The contents of the vessel.
    - `name`: The name of the vessel, if different from the description.

    Attributes:
    - `description`: The contents of the vessel.
    - `name`: The name of the vessel, if different from the description.
    """

    def __init__(self, description: Optional[str] = None, name: Optional[str] = None):
        super().__init__(name=name)
        self.description = description
