from typing import Optional

from flowchem.components.stdlib import Valve
from flowchem.components.stdlib.mapped_component import ComponentMapping


class InjectionValve(Valve):
    """
    A generic injection valve, i.e. a valve with positions 'inject' and 'load'.
    """

    def __init__(
        self, mapping: ComponentMapping = None, name: Optional[str] = None,
    ):
        # Ensure that the mapping is a mapping with 'load' and 'ínject' positions
        if mapping is None:
            mapping = {
                "inject": None,
                "load": None,
            }
        else:
            assert "inject" in mapping
            assert "load" in mapping

        # Call Valve init
        super().__init__(mapping=mapping, name=name)

        # Ensure base state is loading.
        self._base_state = {"setting": "load"}

    async def _update(self):
        # Left to implementations!
        raise NotImplementedError
