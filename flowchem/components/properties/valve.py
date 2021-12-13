from abc import ABC
from typing import MutableMapping, Optional, Union, Dict, Any, Set

from flowchem.components.properties import (
    ActiveComponent,
    Component,
    MappedComponentMixin,
)


class Valve(MappedComponentMixin, ActiveComponent, ABC):
    """
    A generic valve.

    Arguments:
    - `mapping`: The mapping from components to their integer port numbers.
    - `name`: The name of the valve.

    Attributes:
    - `mapping`: The mapping from position name/numbers to components.
    - `name`: The name of the valve.
    - `setting`: The position of the valve as an int or string (mapped via `mapping`).
    """

    def __init__(
        self,
        mapping: Set[Union[int, str]],
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        self.mapping = mapping
        # Base state is first position or 1 if no mapping is provided
        if mapping:
            self.setting = next(iter(mapping))
        else:
            self.setting = "1"

        self._base_state: Dict[str, Any] = {"setting": 1}

    def _validate(self, dry_run):
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping. None provided.")
        return super()._validate(dry_run)
