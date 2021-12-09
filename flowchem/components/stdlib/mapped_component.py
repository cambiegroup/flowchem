import warnings
from typing import Mapping, Union, Optional

from flowchem.components.stdlib import Component
from loguru import logger
from collections import UserDict

ComponentMapping = Mapping[Union[str, int], Optional[Component]]


class distinctdict(UserDict):
    """ Dictionary that does not accept duplicate values except for None.
    From: Expert Python Programming: Become a master in Python by [...], 3rd Edition """

    def __setitem__(self, key, value):
        if value is not None and value in self.values():
            if key not in self or (key in self and self[key] != value):
                raise ValueError(
                    f"Trying to assign the same value to a different key: [{key} => {value}]"
                )
        super().__setitem__(key, value)


class MappedComponentMixin(Component):
    """
    A Mixin to be added to component with mapping.

    All components with mapping should derive from this, both active (e.g. valves) and passive (reactors).

    The mapping has to be provided as follows (e.g. w/ dict):
    - self.mapping = {'mapped_position': 'component_name'}
    where 'mapped_position' can be an int (e.g. multipos. valves) or a string (e.g. 'inject', 'load') for 2-pos valves.
    Values (i.e. components) should be unique, this intrinsically true as the same tubing cannot be connected to two
    different ports, and tubing should be added as node in the graph (thus being a component) anyway.
    The property 'reversed_mapping' is a convenience method to get the reverse mapping, i.e. old behaviour.

    As a side note, this is the opposite key -> value approach used in mw.
    The reason for that is the mapping value can be set on object instantiation (i.e. depend on the device) while the
    mapped component are derived from the graph at runtime.

    For more details on Mixins, see Fluent Python chapter 14 or Effective Python item 41 (links are free for MPG):
    - https://learning.oreilly.com/library/view/fluent-python-2nd/9781492056348/ch14.html#idm45517018812200
    - https://learning.oreilly.com/library/view/effective-python-90/9780134854717/ch05.xhtml#item41


    Arguments:
    - `name`: The name of the component.

    """

    def _validate(self, dry_run):
        self.mapping: ComponentMapping
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping. None provided.")
        assert any(
            [c is not None for c in self.mapping.values()]
        ), f"{self} has no mapped components."
        return super()._validate(dry_run)

    @property
    def reversed_mapping(self):
        """ Return a dictionary of the component's mapping, but with the keys and values swapped. """
        return {v: k for k, v in self.mapping.items()}

    def solve_mapping_values(self, setting):
        """ Test the values provided for the component mapping and resolve them """
        if self.mapping is None:
            raise ValueError(f"{self} requires a mapping. None provided.")

        # A value is given that is a component to map to
        if setting in self.reversed_mapping:
            logger.trace(f"{setting} in {repr(self)}'s mapping.")
            return self.reversed_mapping[setting]

        # the valve's connecting component name was given
        # in this case, we get the mapped valve with that name
        # we don't have to worry about duplicate names since that's checked later

        elif setting in [
            c.name for c in self.reversed_mapping if isinstance(c, Component)
        ]:
            logger.trace(f"{setting} in {repr(self)}'s mapping.")
            mapped_component = [c for c in self.reversed_mapping if c.name == setting]
            return self.reversed_mapping[mapped_component[0]]

        # the user gave the actual port mapping number
        elif setting in self.mapping and isinstance(setting, (int, str)):
            warnings.warn(
                "Mapped component should map with other components not directly to position! "
                "This is deprecated and will remove in future versions.",
                DeprecationWarning,
            )
            logger.trace(f"User supplied manual setting for {self}")
            return setting
        else:
            raise ValueError(f"Invalid setting {setting} for {repr(self)}.")
