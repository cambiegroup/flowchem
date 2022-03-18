""" Represent a generic injection valve. """
from abc import ABC
from typing import Optional

from flowchem.components.properties import ActiveComponent, MultiportComponentMixin


class InjectionValve(MultiportComponentMixin, ActiveComponent, ABC):
    """
    A generic injection valve, i.e. a valve with positions 'inject' and 'load'.
    """

    def __init__(
        self,
        name: Optional[str] = None,
    ):
        # For injection valves, the positions are 'load' and 'inject'
        self.position = {"inject", "load"}
        self.setting = "load"

        # Call Valve init
        super().__init__(name=name)

        # Ensure base state is loading.
        self._base_state = {"setting": "load"}

        # TODO add injection loop volume
