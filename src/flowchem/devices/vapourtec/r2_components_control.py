""" Control module for the Vapourtec R2 valves """
from __future__ import annotations

from typing import TYPE_CHECKING
from loguru import logger
from flowchem import ureg

from flowchem.components.valves.injection_valves import SixPortTwoPosition
from flowchem.components.valves.distribution_valves import TwoPortDistribution
from flowchem.components.pumps.hplc import HPLCPump
from flowchem.components.technical.photo import PhotoControl
from flowchem.components.sensors.base_sensor import Sensor
from flowchem.components.sensors.pressure import PressureSensor
from ...components.technical.power import PowerSwitch

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

    def __init__(self, name: str, hw_device: R2):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/monitor-system", self.monitor_sys, methods=["GET"])
        self.add_api_route("/get-run-state", self.get_run_state, methods=["GET"])
        self.add_api_route(
            "/set-system-max-pressure", self.set_sys_pressure_limit, methods=["PUT"]
        )

    async def monitor_sys(self) -> dict:
        """monitor the system performance"""
        return await self.hw_device.pooling()

    async def get_run_state(self) -> str:
        """Get current system state"""
        return await self.hw_device.get_Run_State()

    async def set_sys_pressure_limit(self, pressure: str) -> bool:
        """Set maximum system pressure: range 1,000 to 50,000 mbar"""
        # TODO: change to accept different units
        await self.hw_device.set_Pressure_limit(pressure)
        return True


class R2PhotoReactor(PhotoControl):
    """R2 reactor control class"""

    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

    # async def get_current_power(self) -> str:
    #     """Get current reactor power state"""
    #     return await self.hw_device.get_current_power()

    async def set_temperature(self, temperature: str) -> bool:
        """Set reactor temperature"""
        await self.hw_device.set_Temperature(temperature)
        return True

    async def get_temperature(self) -> float:
        """Get current reactor temperature"""
        return await self.hw_device.get_current_temperature()

    # async def is_target_reached(self) -> bool:  # type: ignore
    #     """Return True if the set temperature target has been reached."""
    #     c_temp = await self.hw_device.get_current_temperature()
    #     s_temp = await self.hw_device.get_setting_Temperature()
    #     return abs(c_temp - float(s_temp)) <= 1.5

    async def set_UV(self, power: str = "100") -> float:
        """Set UV light intensity at the range 50-100%"""
        await self.hw_device.set_UV(power)
        return True

    async def UV_power_on(self) -> bool:
        """Turn on whole system"""
        await self.hw_device.set_UV("100")
        await self.hw_device.power_on()
        return True

    async def UV_power_off(self) -> bool:
        """Turn off whole system."""
        await self.hw_device.set_UV("0")
        return True


class R2InjectionValve(SixPortTwoPosition):
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    # get position
    position_mapping = {"load": "0", "inject": "1"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    def __init__(self, name: str, hw_device: R2, valve_code: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.valve_code = valve_code

    async def get_position(self) -> str:
        """Get current valve position."""
        position = await self.hw_device.get_valve_Position(self.valve_code)
        # self.hw_device.last_state.valve[self.valve_number]
        return f"position is %s" % self._reverse_position_mapping[position]

    async def set_position(self, position: str) -> bool:
        target_pos = self.position_mapping[position]  # load or inject
        await self.hw_device.trigger_Key_Press(
            str(self.valve_code * 2 + int(target_pos))
        )
        return True


class R2TwoPortValve(TwoPortDistribution):  # total 3 valve (A, B, Collection)
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    # TODO: the mapping name is not applicable
    position_mapping = {"Solvent": "0", "Reagent": "1"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    def __init__(self, name: str, hw_device: R2, valve_code: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.valve_code = valve_code

    async def get_position(self) -> str:
        """Get current valve position."""
        position = await self.hw_device.get_valve_Position(self.valve_code)
        # self.hw_device.last_state.valve[self.valve_number]
        return f"inlet is %s" % self._reverse_position_mapping[position]

    async def set_position(self, position: str) -> bool:
        """Move valve to position."""
        target_pos = self.position_mapping[position]
        await self.hw_device.trigger_Key_Press(
            str(self.valve_code * 2 + int(target_pos))
        )
        return True


class R2HPLCPump(HPLCPump):
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2, pump_code: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.pump_code = pump_code

    # async def get_setting_flow(self) -> str:
    #     """Get current setting flow rate."""
    #     return await self.hw_device.get_setting_Flowrate(self.pump_code)

    async def get_current_flow(self) -> float:
        """Get current flow rate."""
        # return await self.hw_device.pooling()
        return await self.hw_device.get_current_flow(self.pump_code)

    async def set_flowrate(self, flowrate: str) -> bool:
        """Set flow rate to the pump"""
        await self.hw_device.set_Flowrate(self.pump_code, flowrate)
        return True

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """set the flow rate: in ul/min and start infusion."""
        await self.hw_device.set_Flowrate(self.pump_code, rate)
        await self.hw_device.power_on()
        return True

    async def stop(self):
        """Stop infusion"""
        await self.hw_device.set_Flowrate(pump=self.pump_code, flowrate="0 ul/min")

    async def is_pumping(self) -> bool:
        c_flow = await self.hw_device.get_current_flow(self.pump_code)
        return c_flow != 0


class R2PumpPressureSensor(PressureSensor):
    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2, pump_code: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.pump_code = pump_code

    async def read_pressure(self, units: str = "mbar") -> int:  # mbar
        """Get current pump pressure in mbar."""
        return await self.hw_device.get_current_pressure(self.pump_code)


class R2GeneralPressureSensor(PressureSensor):
    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

    async def read_pressure(self, units: str = "mbar") -> int:
        """Get system pressure"""
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
