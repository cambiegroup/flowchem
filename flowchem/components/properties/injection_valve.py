from abc import ABC
from typing import Optional

from flowchem.components.properties import Valve


class InjectionValve(Valve, ABC):
    """
    A generic injection valve, i.e. a valve with positions 'inject' and 'load'.
    """

    def __init__(
        self,
        name: Optional[str] = None,
    ):
        # Ensure that the mapping is a mapping with 'load' and 'ínject' positions
        mapping = {"inject", "load"}

        # Call Valve init
        super().__init__(mapping=mapping, name=name)

        # Ensure base state is loading.
        self._base_state = {"setting": "load"}

