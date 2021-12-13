from typing import Set

from flowchem.components.properties import Component
from loguru import logger


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
    def __init__(self):
        super().__init__()
        self.mapping = set()

    def _validate(self, dry_run):
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping, None provided.")
        assert any(
            [c is not None for c in self.mapping]
        ), f"{self} has no mapped components. Please check the mapping."
        return super()._validate(dry_run)
