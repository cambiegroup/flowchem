from typing import Mapping, Optional, Union, Dict, Any

from flowchem.components.stdlib import ActiveComponent, Component, MappedComponentMixin


class Valve(MappedComponentMixin, ActiveComponent):
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
        mapping: Mapping[Union[int, str], Optional[Component]],
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        # check the mapping's type
        if not isinstance(mapping, (type(None), Mapping)):
            raise TypeError(f"Invalid mapping type {type(mapping)} for {repr(self)}.")
        self.mapping = mapping
        # Base state is first position or 1 if no mapping is provided
        if mapping:
            self.setting = list(self.mapping.keys())[0]
        else:
            self.setting = 1
        self._visualization_shape = "parallelogram"

        self._base_state: Dict[str, Any] = {"setting": 1}

    async def _update(self):
        raise NotImplementedError

    def _validate(self, dry_run):
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping. None provided.")
        return super()._validate(dry_run)
