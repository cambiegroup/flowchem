""" All devices should inherit from this class. """
from __future__ import annotations

from abc import ABC

from fastapi import APIRouter


class BaseDevice(ABC):
    """
    All devices should inherit from `BaseDevice`.

    Attributes:
    - `unique_name`: The name of the component.
    """

    _id_counter = 0

    def __init__(self, name: str | None = None):
        # name the object, either sequentially or with a given name
        if name is None:
            self.name = self.__class__.__name__ + "_" + str(self.__class__._id_counter)
            self.__class__._id_counter += 1
        else:
            self.name = str(name)

    async def initialize(self):
        """
        Initialize the component.

        This method is called upon server init, and before any other command.
        """
        pass

    def get_router(self) -> APIRouter:
        router = APIRouter()

        # Add prefix based on device name
        router_name = self.name.replace(" ", "").lower()
        router.prefix = f"/{router_name}"
        router.tags = [router_name]

        return router

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"

    def __str__(self):
        return f"{self.__class__.__name__} {self.name}"
