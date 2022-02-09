from abc import ABC
from typing import Optional, Union, Dict, Any, Set

from flowchem.components.properties import (
    ActiveComponent,
    MultiportComponentMixin,
)


class Valve(MultiportComponentMixin, ActiveComponent, ABC):
    """
    A generic valve.

    Arguments:
    - `port`: The port numbers.
    - `name`: The name of the valve.
    """

    def __init__(
        self,
        port: Set[Union[int, str]],
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        self.port = port
        # Base state is first port or 1 if no port is provided
        if port:
            self.setting = next(iter(port))
        else:
            self.setting = 1

        self._base_state: Dict[str, Any] = {"setting": 1}

    def _validate(self, dry_run):
        if not self.port:
            raise ValueError(f"The port names for valve {self} are not valid.")
        return super()._validate(dry_run)
