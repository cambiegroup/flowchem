""" Router for a Spinsolve object """
from fastapi import APIRouter
from flowchem import Spinsolve


def spinsolve_get_router(device: Spinsolve) -> APIRouter:
    """ Adds an APIRouter on top of an existing Spinsolve object """
    router = APIRouter()

    @router.get("/solvent")
    async def get_solvent():
        """

        Returns:

        """
        return device.solvent

    @router.put("/solvent/{solvent_name}")
    async def set_solvent(solvent_name: str):
        """

        Args:
            solvent_name:
        """
        device.solvent = solvent_name

    @router.get("/sample-name")
    async def get_sample():
        """

        Returns:

        """
        return device.sample

    @router.put("/sample-name/{value}")
    async def set_sample(value: str):
        """

        Args:
            value:
        """
        device.sample = value

    return router
