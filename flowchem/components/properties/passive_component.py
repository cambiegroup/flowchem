""" All devices should inherit from this class. """
from flowchem.components.properties import Component


class PassiveComponent(Component):
    """A non-connected, non-controllable, passive component."""

    _id_counter = 0
