from flowchem.components.properties import Component
from flowchem.units import flowchem_ureg


class Channel(Component):
    """
    A reaction channel.

    Arguments:
    - `length`: The length of the channel as a str.
    - `volume`: The channel volume as a str.
    - `material`: The material around the channel.

    """

    _id_counter = 0

    def __init__(self, length: str, volume: str, material: str, name: str = None):
        """
        See the `Tube` attributes for a description of the arguments.
        """
        self.length = flowchem_ureg.parse_expression(length)
        self.volume = flowchem_ureg.parse_expression(volume)

        self.material = material

        super().__init__(name)

    def __repr__(self):
        return f"Channel of length {self.length} and volume {self.volume}"
