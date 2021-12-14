from abc import ABC
from typing import Optional

from components.properties import MappedComponentMixin, ActiveComponent


class InjectionValve(MappedComponentMixin, ActiveComponent, ABC):
    """
    A generic injection valve, i.e. a valve with positions 'inject' and 'load'.
    """

    def __init__(
        self,
        name: Optional[str] = None,
    ):
        # Ensure that the mapping is a mapping with 'load' and 'inject' positions
        self.mapping = {"inject", "load"}
        self.setting = "load"

        # Call Valve init
        super().__init__(name=name)

        # Ensure base state is loading.
        self._base_state = {"setting": "load"}

