""" Router for a Spinsolve object """
from fastapi import APIRouter
from flowchem import Spinsolve


def spinsolve_get_router(device: Spinsolve):
    """
    :param device: object of Spinsolve type to be controlled
    :return:
    """
    router = APIRouter()

    @router.get("/solvent")
    async def get_solvent():
        return device.solvent

    @router.put("/solvent/{solvent_name}")
    async def set_solvent(solvent_name: str):
        device.solvent = solvent_name

    @router.get("/sample-name")
    async def get_sample():
        return device.sample

    @router.put("/sample-name/{value}")
    async def set_sample(value: str):
        device.sample = value

    return router
