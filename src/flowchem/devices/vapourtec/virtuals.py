from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vapourtec.r2_components_control import (
    R2GeneralPressureSensor,
    R2GeneralSensor,
    R2HPLCPump,
    R2InjectionValve,
    R2MainSwitch,
    R2PumpPressureSensor,
    R2TwoPortValve,
    R4Reactor,
    UV150PhotoReactor,
)
from flowchem.devices.vapourtec.r4_heater_channel_control import R4HeaterChannelControl
from flowchem.components.technical.temperature import TempRange
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
from collections import namedtuple
import pint


class VirtualR2(FlowchemDevice):

    def __init__(self, name: str = "", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Vitual Vapourtec"
        self.device_info.model = "Vitual R2 reactor module"

        self._min_t = [-40]*4
        self._max_t = [80]*4

        self._temp = [20]*4 # Channel 1, 2, 3, 4
        self._flow = {"A": 10, "B": 10} # Pump A, B
        self._valve_pos = ["0"]*5 # Valve 0,..,4
        self._pressure = [ureg.Quantity("2000 mbar")]*3 # Pump 0, 1
        self._intensity = 10

    async def initialize(self):
        list_of_components = [
            R2MainSwitch("Power", self), # type: ignore
            R2GeneralPressureSensor("PressureSensor", self), # type: ignore
            R2GeneralSensor("GSensor2", self), # type: ignore
            UV150PhotoReactor("PhotoReactor", self), # type: ignore
            R2HPLCPump("Pump_A", self, "A"), # type: ignore
            R2HPLCPump("Pump_B", self, "B"), # type: ignore
            R2TwoPortValve("ReagentValve_A", self, 0), # type: ignore
            R2TwoPortValve("ReagentValve_B", self, 1), # type: ignore
            R2TwoPortValve("CollectionValve", self, 4), # type: ignore
            R2InjectionValve("InjectionValve_A", self, 2), # type: ignore
            R2InjectionValve("InjectionValve_B", self, 3), # type: ignore
            R2PumpPressureSensor("PumpSensor_A", self, 0), # type: ignore
            R2PumpPressureSensor("PumpSensor_B", self, 1), # type: ignore
        ]
        self.components.extend(list_of_components)

        # Create components for reactor bays
        reactor_temp_limits = {
            ch_num: TempRange(min=ureg.Quantity(t[0]), max=ureg.Quantity(t[1]))
            for ch_num, t in enumerate(zip(self._min_t, self._max_t, strict=True))
        }

        reactors = [
            R4Reactor(f"reactor-{n + 1}", self, n, reactor_temp_limits[n]) # type: ignore
            for n in range(4)
        ]
        self.components.extend(reactors)

    async def version(self):
        return "VIRTUAL"

    async def set_flowrate(self, pump: str, flowrate: str):
        logger.debug(f"Send {flowrate} to the pump {pump} - Virtual R2")
        if flowrate.isnumeric():
            flowrate = flowrate + "ul/min"
            logger.warning(
                "No units provided to set_temperature, assuming microliter/minutes.",
            )
        parsed_f = ureg.Quantity(flowrate)
        self._flow[pump] = parsed_f.magnitude

    async def get_current_flow(self, pump_code: str) -> float:
        return self._flow[pump_code]

    async def get_current_temperature(self, channel) -> float:
        return self._temp[channel]

    async def get_target_temperature(self, channel) -> float:
        return self._temp[channel]

    async def set_temperature(
        self,
        channel: int,
        temp: pint.Quantity,
        heating: bool | None = None,
        ramp_rate: str = "80",
    ):
        logger.debug(f"Send {temp} to the channel {channel} - Virtual R2")
        self._temp[channel] = temp.magnitude

    async def set_UV150(self, power: int):
        logger.debug(f"Send power {power} to the UV150 - Virtual R2")

    async def get_current_pressure(self, pump_code: int = 2) -> pint.Quantity:
        return self._pressure[pump_code]

    async def set_pressure_limit(self, pressure: str):
        logger.debug(f"Send pressure limit {pressure} - Virtual R2")

    async def trigger_key_press(self, keycode: str):
        logger.debug(f"Trigger key pressure {keycode} - Virtual R2")

    async def power_on(self):
        ...

    async def power_off(self):
        ...

    async def get_valve_position(self, valve_code: int) -> str:
        return self._valve_pos[valve_code]

    async def pooling(self) -> dict:
        return {}

    async def get_state(self) -> str:
        return "1"


class VirtualR4Heater(FlowchemDevice):

    ChannelStatus = namedtuple("ChannelStatus", "state, temperature")

    def __init__(self, name: str = "", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Vitual Vapourtec"
        self.device_info.model = "R4 reactor module virtual"

        self._min_t = [-100]*4
        self._max_t = [250]*4

    async def initialize(self):
        temp_limits = {
            ch_num: TempRange(
                min=ureg.Quantity(f"{t[0]} °C"),
                max=ureg.Quantity(f"{t[1]} °C"),
            )
            for ch_num, t in enumerate(zip(self._min_t, self._max_t, strict=True))
        }
        reactor_positions = [
            R4HeaterChannelControl(f"reactor{n + 1}", self, n, temp_limits[n]) # type: ignore
            for n in range(4)
        ]
        self.components.extend(reactor_positions)
        self._temp = {i: 20 for i in range(len(self.components))}

    async def set_temperature(self, channel, temperature: pint.Quantity):
        logger.debug(f"Set temperature {temperature} to the channel {channel} - R4Heater Virtual")
        self._temp[channel] = temperature.magnitude

    async def get_temperature(self, channel):
        return self._temp[channel]

    async def get_status(self, channel):
        s = VirtualR4Heater.ChannelStatus
        s.state = "S"
        return s

    async def power_on(self, channel):
        ...

    async def power_off(self, channel):
        ...



