from typing import Optional

from flowchem.components.properties import PassiveMixer


class YMixer(PassiveMixer):
    """
    A Y mixer.

    This is an alias of `Component`.

    Arguments:
    - `name`: The name of the mixer.

    Attributes:
    - See arguments.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
