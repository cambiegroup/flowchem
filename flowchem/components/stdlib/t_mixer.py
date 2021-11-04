from typing import Optional

from flowchem.components.stdlib import Mixer


class TMixer(Mixer):
    """
    A T mixer.

    This is an alias of `Component`.

    Arguments:
    - `name`: The name of the mixer.

    Attributes:
    - `name`: The name of the mixer.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
