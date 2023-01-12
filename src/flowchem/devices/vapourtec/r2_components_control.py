""" Control module for the Vapourtec R2 valves """
from __future__ import annotations

from typing import TYPE_CHECKING
import pint

from flowchem.components.valves.injection_valves import SixPortTwoPosition
from flowchem.components.valves.distribution_valves import TwoPortDistribution
from flowchem.components.pumps.hplc import HPLCPump
from flowchem.components.base_component import FlowchemComponent

if TYPE_CHECKING:
    from .r2 import R2
    from .r4_heater import R4Heater

AllValveDic = {"TwoPortValve_A": 0,
               "TwoPortValve_B": 1,
               "InjectionValve_A": 2,
               "InjectionValve_B": 3,
               "TwoPortValve_C": 4
               }
AllPumpDic = {"HPLCPump_A": 0,
              "HPLCPump_B": 1
              }


class R2Main(FlowchemComponent):
    """R2 reactor control class"""

    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

    async def power_on(self):
        """Turn on whole system"""
        return await self.hw_device.power_on()

    async def power_off(self):
        """Turn off whole system."""
        return await self.hw_device.power_off()

    async def monitor_sys(self) -> dict:
        """monitor the system performance"""
        return await self.hw_device.pooling()

    async def get_run_state(self) -> str:
        """Get current system state"""
        return await self.hw_device.get_Run_State()

    async def set_temperature(self, temp: str):
        """Set reactor temperature"""
        await self.hw_device.set_Temperature(temp)

    async def get_setting_temperature(self) -> str:
        """Get setting temperature"""
        return await self.hw_device.get_setting_Temperature()

    async def get_current_temperature(self) -> float:
        """Get current reactor temperature"""
        return await self.hw_device.get_current_temperature()

    async def set_UV(self, power: str = "100"):
        """Set UV light intensity at the range 50-100%"""
        await self.hw_device.set_UV(power)

    async def get_current_power(self) -> str:
        """Get current reactor power state"""
        return await self.hw_device.get_current_power()

    async def get_sys_pressure(self) -> int:
        """Get system pressure"""
        return await self.hw_device.get_current_pressure()

    async def set_sys_pressure_limit(self, pressure : str):
        """Set maximum system pressure: range 1,000 to 50,000 mbar"""
        await self.hw_device.set_Pressure_limit(pressure)
    async def get_setting_Pressure_Limit(self) -> str:
        """Get setting system pressure limit"""
        return await self.hw_device.get_setting_Pressure_Limit()


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

    async def set_position(self, position: str):
        target_pos = self.position_mapping[position]
        await self.hw_device.trigger_Key_Press(str(self.valve_code * 2 + int(target_pos)))


class R2TwoPortValve(TwoPortDistribution):  # total 3 valve (A, B, Collection)
    """R2 reactor injection loop valve control class."""
    hw_device: R2  # for typing's sake

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

    async def set_position(self, position: str):
        """Move valve to position."""
        target_pos = self.position_mapping[position]
        await self.hw_device.trigger_Key_Press(str(self.valve_code * 2 + int(target_pos)))


class R2HPLCPump(HPLCPump):
    """R2 reactor injection loop valve control class."""
    hw_device: R2  # for typing's sake

    def __init__(self, name: str, hw_device: R2, pump_code: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.pump_code = pump_code

    async def get_setting_flow(self) -> str:
        """Get current setting flow rate."""
        return await self.hw_device.get_setting_Flowrate(self.pump_code)

    async def get_current_flow(self) -> float:
        """Get current flow rate."""
        # return await self.hw_device.pooling()
        return await self.hw_device.get_current_flow(self.pump_code)

    async def set_flowrate(self, flowrate: str):
        """Set flow rate to the pump"""
        await self.hw_device.set_Flowrate(self.pump_code, flowrate)

    async def get_current_pressure(self) -> int:
        """Get current pump pressure."""
        return await self.hw_device.get_current_pressure(self.pump_code)
