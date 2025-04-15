from flowchem.components.technical.temperature import TempRange
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.huber.huber_temperature_control import HuberTemperatureControl
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import pint


class FakeSerial:
    name = "COMX"
    temp = "0°C"

class VirtualHuberChiller(FlowchemDevice):

    def __init__(self, name="", **kwargs) -> None:
        super().__init__(name)
        self._min_t: float = kwargs.get("min_temp", -150)
        self._max_t: float = kwargs.get("max_temp", 250)

        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer="Huber"
        self.device_info.model="generic chiller"

        self.temp = ureg.Quantity("0 °C")

    async def initialize(self):
        temperature_range = TempRange(
            min=ureg.Quantity(f"{self._min_t} °C"),
            max=ureg.Quantity(f"{self._max_t} °C"),
        )
        # Set TemperatureControl component.
        self.components.append(
            HuberTemperatureControl("temperature-control", self, temperature_range) # type: ignore
        )
        logger.debug("Virtual HuberChiller initialized")

    @classmethod
    def from_config(cls, **kwargs):
        return cls(**kwargs)

    async def set_temperature(self, temp: pint.Quantity):
        self.temp = temp
        logger.debug(f"Virtual HuberChiller set the temperature to {temp}")

    async def get_temperature(self) -> float:
        return ureg.Quantity(self.temp).magnitude

    async def target_reached(self) -> bool:
        return True

    async def _send_command_and_read_reply(self, command: str) -> str:
        logger.debug(f"Virtual HuberChillerreceived command: {command}")
        return "ok"