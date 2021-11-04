from typing import Set, Optional


class Component(object):
    """
    One of the individual, irreducible parts of a flow chemistry setup.

    All components in an `Apparatus` must be of type `Component`.
    However, it is unlikely that a user will directly instantiate a `Component`.

    Arguments:
    - `name`: The name of the component.

    Attributes:
    - `name`: The name of the component.
    """

    _id_counter = 0
    _used_names: Set[str] = set()

    def __init__(self, name: Optional[str] = None):
        # name the object, either sequentially or with a given name
        if name is None:
            self.name = self.__class__.__name__ + "_" + str(self.__class__._id_counter)
            self.__class__._id_counter += 1
        else:
            self.name = str(name)
        self._visualization_shape = "box"

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"

    def __str__(self):
        return f"{self.__class__.__name__} {self.name}"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    def _validate(self, dry_run):
        """Components are valid for dry runs, but not for real runs."""
        if not dry_run:
            raise RuntimeError
