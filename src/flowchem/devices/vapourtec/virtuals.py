from .r2 import R2
from .r4_heater import R4Heater
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from collections.abc import Iterable
from loguru import logger
import pint


class VirtualR2(R2):

    def __init__(
        self,
        name: str = "",
        rt_temp: float = 27,  # todo: find a way to
        min_temp: float | list[float] = -40,
        max_temp: float | list[float] = 80,
        min_pressure: float = 1000,
        max_pressure: float = 50000,
        **config,
    ) -> None:

        # Set min and max temp for R4 heater
        if not isinstance(min_temp, Iterable):
            min_temp = [min_temp] * 4
        if not isinstance(max_temp, Iterable):
            max_temp = [max_temp] * 4
        assert len(min_temp) == len(max_temp) == 4

        self.rt_t = rt_temp * ureg.degreeC
        self._min_t = min_temp * ureg.degreeC
        self._max_t = max_temp * ureg.degreeC

        self._heated = True  # to saving the dry ice
        self._intensity = 0

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Vapourtec",
            model="R2 reactor module",
        )

        self.name = name
        self.components = []
        self._intensity = 10

    async def version(self):
        return "VIRTUAL"

    async def set_flowrate(self, pump: str, flowrate: str):
        logger.debug(f"Send {flowrate} to the pump {pump} - Virtual R2")

    async def get_current_temperature(self, channel) -> float:
        return 20

    async def get_target_temperature(self, channel) -> float:
        return 50

    async def set_temperature(
        self,
        channel: int,
        temp: pint.Quantity,
        heating: bool | None = None,
        ramp_rate: str = "80",
    ):
        logger.debug(f"Send {temp} to the channel {channel} - Virtual R2")

    async def set_UV150(self, power: int):
        logger.debug(f"Send power {power} to the UV150 - Virtual R2")

    async def get_current_pressure(self, pump_code: int = 2) -> pint.Quantity:
        return ureg.Quantity("2000 mbar")

    async def set_pressure_limit(self, pressure: str):
        logger.debug(f"Send pressure limit {pressure} - Virtual R2")

    async def trigger_key_press(self, keycode: str):
        logger.debug(f"Trigger key pressure {keycode} - Virtual R2")

    async def power_on(self):
        ...

    async def power_off(self):
        ...

    async def get_current_flow(self, pump_code: str) -> float:
        return 20

    async def get_valve_position(self, valve_code: int) -> str:
        return "0"

    async def pooling(self) -> dict:
        return {}

    async def get_state(self) -> str:
        return "1"


class VirtualR4Heater(R4Heater):

    def __init__(
        self,
        name: str = "",
        min_temp: float | list[float] = -100,
        max_temp: float | list[float] = 250,
        **config,
    ) -> None:
        # Set min and max temp for all 4 channels
        if not isinstance(min_temp, Iterable):
            min_temp = [min_temp] * 4
        if not isinstance(max_temp, Iterable):
            max_temp = [max_temp] * 4
        assert len(min_temp) == len(max_temp) == 4
        self._min_t = min_temp
        self._max_t = max_temp

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Vapourtec",
            model="R4 reactor module virtual",
        )

        self.name = name
        self.components = []

    async def initialize(self):
        await super().initialize()
        self._temp = {i: 10 for i in range(len(self.components))}

    async def version(self):
        return "VIRTUAL"

    async def set_temperature(self, channel, temperature: pint.Quantity):
        logger.debug(f"Set temperature {temperature} to the channel {channel} - R4Heater Virtual")
        self._temp[channel] = temperature.magnitude

    async def get_temperature(self, channel):
        return self._temp[channel]

    async def get_status(self, channel):
        s = self.ChannelStatus
        s.state = "S"
        return s

    async def power_on(self, channel):
        ...

    async def power_off(self, channel):
        ...



