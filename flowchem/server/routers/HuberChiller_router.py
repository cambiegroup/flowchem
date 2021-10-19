""" Router for a HuberChiller object """
from fastapi import APIRouter
from flowchem import HuberChiller


def spinsolve_get_router(device: HuberChiller) -> APIRouter:
    """ Adds an APIRouter on top of an existing Spinsolve object """
    router = APIRouter()

    router.add_api_route("/temperature/setpoint", device.get_temperature_setpoint, methods=["GET"])

    @router.get("/temperature/setpoint")
    async def get_temp_setpoint():
        return await device.get_temperature_setpoint()

    @router.put("/temperature/setpoint")
    async def set_temp_setpoint(temperature: float):
        await device.set_temperature_setpoint(temperature)

    @router.get("/temperature/internal")
    async def get_int_t():
        return await device.internal_temperature()

    @router.get("/temperature/return")
    async def get_return_t():
        return await device.return_temperature()

    @router.get("/pump/pressure")
    async def get_pump_p():
        return await device.pump_pressure()

    @router.get("/pump/speed")
    async def get_pump_s():
        return await device.pump_speed()

    @router.get("/pump/speed/setpoint")
    async def get_pump_s_setpoint():
        return await device.pump_speed_setpoint()

    @router.put("/pump/speed/setpoint")
    async def put_pump_s_setpoint(speed: int):
        return await device.set_pump_speed(speed)

    return router