from .chiller import HuberChiller, TempRange, HuberTemperatureControl
from flowchem import ureg
from loguru import logger
import pint


class FakeSerial:
    name = "COMX"
    temp = "0°C"

class VirtualHuberChiller(HuberChiller):

    async def initialize(self):
        temperature_range = TempRange(
            min=ureg.Quantity(f"{self._min_t} °C"),
            max=ureg.Quantity(f"{self._max_t} °C"),
        )
        # Set TemperatureControl component.
        self.components.append(
            HuberTemperatureControl("temperature-control", self, temperature_range)
        )
        logger.debug(f"Virtual HuberChiller initialized")

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs):
        return cls(FakeSerial, name)

    async def set_temperature(self, temp: pint.Quantity):
        self._serial.temp = temp
        logger.debug(f"Virtual HuberChiller set the temperature to {temp}")

    async def get_temperature(self) -> float:
        return ureg.Quantity(self._serial.temp).magnitude

    async def target_reached(self) -> bool:
        return True

    async def _send_command_and_read_reply(self, command: str) -> str:
        logger.debug(f"Virtual HuberChillerreceived command: {command}")
        return "ok"