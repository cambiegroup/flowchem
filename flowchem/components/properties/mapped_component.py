from typing import Optional, Set, Union

from flowchem.components.properties import Component


class MultiportComponentMixin(Component):
    """
    A Mixin to be added to component with more than 1 inlet or outlet port.

    All components with multimple ports should derive from this to ensure proper validation of the port positions.

    The port names have to be provided as follows (e.g. w/ a set, ensuring unique names):
    - self.port = {'position_name_1', 'position_name_2'}
    where 'position_name_1' can be an int (e.g. multipos. valves) or a string (e.g. 'inject', 'load') for 2-pos valves.
    The port names specified will be used as edge attributes in the graph (attrs. from_position and to_position).

    A Mixin is used to prefer composition to inheritance, see en.wiki:Composition_over_inheritance.
    For more details on Mixins in Python, Fluent Python chapter 14 or Effective Python item 41 (links are free for MPG):
    - https://learning.oreilly.com/library/view/fluent-python-2nd/9781492056348/ch14.html#idm45517018812200
    - https://learning.oreilly.com/library/view/effective-python-90/9780134854717/ch05.xhtml#item41


    Arguments:
    - `name`: The name of the component.

    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self.port: Set[Union[str, int]] = set()

    def _validate(self, dry_run):
        if not self.port:
            raise ValueError(f"{self} requires a mapping, None provided.")
        assert any(
            [c is not None for c in self.port]
        ), f"{self} has no mapped components. Please check the mapping."
        return super()._validate(dry_run)
