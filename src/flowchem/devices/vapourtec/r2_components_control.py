"""Control module for the Vapourtec R2 valves."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.pumps.hplc import HPLCPump
from flowchem.components.sensors.base_sensor import Sensor
from flowchem.components.sensors.pressure import PressureSensor
from flowchem.components.technical.photo import Photoreactor
from flowchem.components.technical.power import PowerSwitch
from flowchem.components.technical.temperature import TemperatureControl, TempRange
from flowchem.components.valves.distribution_valves import TwoPortDistribution
from flowchem.components.valves.injection_valves import SixPortTwoPosition

if TYPE_CHECKING:
    from .r2 import R2

AllValveDic = {
    "TwoPortValve_A": 0,
    "TwoPortValve_B": 1,
    "InjectionValve_A": 2,
    "InjectionValve_B": 3,
    "TwoPortValve_C": 4,
}
AllPumpDic = {"HPLCPump_A": 0, "HPLCPump_B": 1}


class R2GeneralSensor(Sensor):
    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2) -> None:
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/monitor-system", self.monitor_sys, methods=["GET"])
        self.add_api_route("/get-run-state", self.get_run_state, methods=["GET"])
        self.add_api_route(
            "/set-system-max-pressure",
            self.set_sys_pressure_limit,
            methods=["PUT"],
        )

    async def monitor_sys(self) -> dict:
        """Monitor system performance."""
        return await self.hw_device.pooling()

    async def get_run_state(self) -> str:
        """Get current system state."""
        return await self.hw_device.get_state()

    async def set_sys_pressure_limit(self, pressure: str) -> bool:
        """Set maximum system pressure: range 1,000 to 50,000 mbar."""
        # TODO: change to accept different units
        await self.hw_device.set_pressure_limit(pressure)
        return True


class R4Reactor(TemperatureControl):
    """R4 reactor heater channel controlled via the R2."""

    hw_device: R2  # for typing's sake

    def __init__(
        self, name: str, hw_device: R2, channel: int, temp_limits: TempRange
    ) -> None:
        """Create a TemperatureControl object."""
        super().__init__(name, hw_device, temp_limits)
        self.channel = channel

    async def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        set_t = await super().set_temperature(temp)
        return await self.hw_device.set_temperature(self.channel, set_t)

    async def get_temperature(self) -> float:  # type: ignore
        """Return temperature in Celsius."""
        # TODO:
        raise NotImplementedError

    async def is_target_reached(self) -> bool:  # type: ignore
        """Return True if the set temperature target has been reached."""
        # TODO:
        raise NotImplementedError

    async def power_on(self):
        """Turn on temperature control."""
        return await self.hw_device.power_on()

    async def power_off(self):
        """Turn off temperature control."""
        return await self.hw_device.power_off()


class UV150PhotoReactor(Photoreactor):
    """R2 reactor control class."""

    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2) -> None:
        super().__init__(name, hw_device)
        self._intensity = 0  # 0 set upon device init

    async def set_intensity(self, percent: int = 100):
        """Set UV light intensity at the range 50-100%."""
        self._intensity = percent
        await self.hw_device.set_UV150(percent)

    async def get_intensity(self) -> int:
        """Return last set intensity."""
        return self._intensity

    async def power_on(self):
        """Turn on the whole system, no way to power UV150 independently."""
        if self._intensity:
            await self.hw_device.power_on()
            return
        logger.error("UV150 power on requested without setting intensity first!")

    async def power_off(self):
        """Turn off light."""
        self._intensity = 0
        await self.hw_device.set_UV150(0)


class R2InjectionValve(SixPortTwoPosition):
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    # get position
    position_mapping = {"load": "0", "inject": "1"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    def __init__(self, name: str, hw_device: R2, valve_code: int) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.valve_code = valve_code

    async def get_position(self) -> str:
        """Get current valve position."""
        position = await self.hw_device.get_valve_Position(self.valve_code)
        return "position is %s" % self._reverse_position_mapping[position]

    async def set_position(self, position: str) -> bool:
        """Set position: 'load' or 'inject'."""
        target_pos = self.position_mapping[position]  # load or inject
        await self.hw_device.trigger_key_press(
            str(self.valve_code * 2 + int(target_pos)),
        )
        return True


class R2TwoPortValve(TwoPortDistribution):  # total 3 valve (A, B, Collection)
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    # TODO: the mapping name is not applicable
    position_mapping = {"Solvent": "0", "Reagent": "1"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    def __init__(self, name: str, hw_device: R2, valve_code: int) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.valve_code = valve_code

    async def get_position(self) -> str:
        """Get current valve position."""
        position = await self.hw_device.get_valve_Position(self.valve_code)
        # self.hw_device.last_state.valve[self.valve_number]
        return "inlet is %s" % self._reverse_position_mapping[position]

    async def set_position(self, position: str) -> bool:
        """Move valve to position."""
        target_pos = self.position_mapping[position]
        await self.hw_device.trigger_key_press(
            str(self.valve_code * 2 + int(target_pos)),
        )
        return True


class R2HPLCPump(HPLCPump):
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2, pump_code: str) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.pump_code = pump_code

    async def get_current_flow(self) -> float:
        """Get current flow rate."""
        return await self.hw_device.get_current_flow(self.pump_code)

    async def set_flowrate(self, flowrate: str) -> bool:
        """Set flow rate to the pump."""
        await self.hw_device.set_flowrate(self.pump_code, flowrate)
        return True

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Set the flow rate: in ul/min and start infusion."""
        if volume:
            logger.warning(f"Volume parameter ignored: not supported by {self.name}!")

        await self.hw_device.set_flowrate(self.pump_code, rate)
        await self.hw_device.power_on()
        return True

    async def stop(self):
        """Stop infusion."""
        await self.hw_device.set_flowrate(pump=self.pump_code, flowrate="0 ul/min")

    async def is_pumping(self) -> bool:
        c_flow = await self.hw_device.get_current_flow(self.pump_code)
        return c_flow != 0


class R2PumpPressureSensor(PressureSensor):
    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2, pump_code: int) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.pump_code = pump_code

    async def read_pressure(self, units: str = "mbar") -> int | None:  # mbar
        """Get current pump pressure in mbar."""
        return await self.hw_device.get_current_pressure(self.pump_code)


class R2GeneralPressureSensor(PressureSensor):
    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

    async def read_pressure(self, units: str = "mbar") -> int:
        """Get system pressure."""
        # TODO: now the output are always mbar, change it to fit the base component
        return await self.hw_device.get_current_pressure()


class R2MainSwitch(PowerSwitch):
    hw_device: R2  # just for typing

    async def power_on(self) -> bool:
        await self.hw_device.power_on()
        return True

    async def power_off(self) -> bool:
        await self.hw_device.power_off()
        return True
