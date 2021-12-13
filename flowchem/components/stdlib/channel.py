from flowchem.units import flowchem_ureg


class Channel:
    """
    A reaction channel.

    Arguments:
    - `length`: The length of the channel as a str.
    - `volume`: The channel volume as a str.
    - `material`: The material around the channel.

    """

    channel_counter = 0

    def __init__(self, length: str, volume: str, material: str, name: str = None):
        """
        See the `Tube` attributes for a description of the arguments.
        """
        self.length = flowchem_ureg.parse_expression(length)
        self.volume = flowchem_ureg.parse_expression(volume)

        self.material = material

        if name is None:
            Channel.channel_counter += 1
            self.name = f"Tube_{Channel.channel_counter}"
        else:
            self.name = name

    def __repr__(self):
        return f"Channel of length {self.length} and volume {self.volume}"
