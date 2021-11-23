from flowchem.components.stdlib import Component


class MappedComponentMixin(Component):
    """
    A Mixin to be added to component with mapping.

    For more details on Mixins, see Fluent Python chapter 14 or Effective Python item 41 (links are free for MPG):
    - https://learning.oreilly.com/library/view/fluent-python-2nd/9781492056348/ch14.html#idm45517018812200
    - https://learning.oreilly.com/library/view/effective-python-90/9780134854717/ch05.xhtml#item41

    All components with mapping should derive from this, both active (e.g. valves) and passive (reactors).

    Arguments:
    - `name`: The name of the component.

    """

    def _validate(self, dry_run):
        if not self.mapping:
            raise ValueError(f"{self} requires a mapping. None provided.")
        return super()._validate(dry_run)
