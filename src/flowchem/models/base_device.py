"""All devices should inherit from this class."""
from __future__ import annotations

from abc import ABC

from fastapi import APIRouter


class BaseDevice(ABC):
    """
    All devices should inherit from `BaseDevice`.

    Attributes:
    - `name`: The unique name of the component.
    """

    _id_counter = 0

    def __init__(self, name: str | None = None):
        """Ensure the device name validity."""
        # Ensure a name is provided for the object, either sequentially or with a given name
        if name is None:
            self.name = self.__class__.__name__ + "_" + str(self.__class__._id_counter)
            self.__class__._id_counter += 1
        else:
            self.name = str(name)

        # Support for OWL classes
        # noinspection HttpUrlsUsage
        self.owl_subclass_of = {"http://purl.obolibrary.org/obo/OBI_0000968"}

    async def initialize(self):
        """
        Initialize the component.

        This method is called upon server init, and before any other command.
        """

    def get_router(self, prefix: str | None = None) -> APIRouter:
        """Return fastapi APIRouter object with instance routes."""
        if prefix:
            assert prefix.startswith("/"), "Prefix must start with '/'"

        # Add prefix based on device name + eventually additional prefix (subcomponents)
        router_name = self.name.replace(" ", "").lower()
        router = APIRouter(prefix=f"/{router_name}{prefix or ''}")
        router.tags = [router_name]

        return router

    def __repr__(self):
        """Representation including instance name."""
        try:
            return f"<{self.__class__.__name__} {self.name}>"
        except AttributeError:
            return f"<{self.__class__.__name__} Unknown>"

    def __str__(self):
        """Str representation including instance name."""
        try:
            return f"{self.__class__.__name__} {self.name}"
        except AttributeError:
            return f"<{self.__class__.__name__} Unknown>"
