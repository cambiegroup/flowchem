""" A vessel, optionally with info on the chemical input contained. """
from typing import Optional

from ord_schema.proto.reaction_pb2 import ReactionInput

from flowchem.components.properties import Component


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
        self.chemical = None

    def _validate(self, dry_run):
        # If chemical info are provided, they should be ReactionInput
        if self.chemical is not None:
            assert isinstance(
                self.chemical, ReactionInput
            ), "Vessel have a ReactionInput"
