""" Example device with builtin router support """
from fastapi import APIRouter


class FakeDevice:
    """
    Templating fake device
    """

    def __init__(self, port):
        self.port = port
        self._temp = 20

    def get_router(self):
        """Returns the router object."""
        router = APIRouter()

        @router.get("/temperature")
        async def get_temp():
            """Fake function returning temperature"""
            return self.temperature

        @router.put("/temperature/{temp}")
        async def set_temp(temp: float):
            """Fake temperature setter."""
            self.temperature = temp

        return router

    @property
    def temperature(self):
        """
        Example device property.

        :return: temperature
        """
        return self._temp

    @temperature.setter
    def temperature(self, temp: int):
        self._temp = temp
