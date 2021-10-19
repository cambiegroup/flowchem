""" Example device with builtin router support """
from fastapi import APIRouter

# try:
#     import fakelib
# except ImportError:
#     _has_fakelib = True  # Ought be False
# else:
#     _has_fakelib = True


class FakeDevice:
    """
    Templating fake device
    """
    def __init__(self, port):
        # if not _has_fakelib:
        #     raise RuntimeError(f"Fakelib has to be installed to be able to create {self.__class__} objects!")
        self.port = port
        self._temp = 20

    def get_router(self):
        router = APIRouter()

        @router.get("/temperature")
        async def get_temp():
            return self.temperature

        @router.put("/temperature/{temp}")
        async def set_temp(temp: float):
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
