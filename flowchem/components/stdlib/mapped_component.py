import warnings
from flowchem.components.stdlib import Component
from loguru import logger


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

    def solve_mapping_values(self, setting):
        """ Test the values provided for the component mapping and resolve them """
        if self.mapping is None:
            raise ValueError(f"{self} requires a mapping. None provided.")

        # A value is given that is a component to map to
        if setting in self.mapping:
            logger.trace(f"{setting} in {repr(self)}'s mapping.")
            return self.mapping[setting]

        # the valve's connecting component name was given
        # in this case, we get the mapped valve with that name
        # we don't have to worry about duplicate names since that's checked later
        elif setting in [c.name for c in self.mapping]:
            logger.trace(f"{setting} in {repr(self)}'s mapping.")
            mapped_component = [c for c in self.mapping if c.name == setting]
            return self.mapping[mapped_component[0]]

        # the user gave the actual port mapping number
        elif setting in self.mapping.values() and isinstance(setting, int):
            warnings.warn("Mapped component should map with other components not directly to position! "
                          "This is deprecated and will remove in future versions.", DeprecationWarning)
            logger.trace(f"User supplied manual setting for {self}")
            return setting
        else:
            raise ValueError(f"Invalid setting {setting} for {repr(self)}.")
