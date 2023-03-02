from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem import ureg
from flowchem.components.base_component import FlowchemComponent
from flowchem.components.sensors.pressure import PressureSensor
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .el_flow import MFC, EPC


class EPCComponent(PressureSensor):
    hw_device: EPC  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic power supply"""
        super().__init__(name, hw_device)
        self.add_api_route("/get-pressure", self.get_pressure, methods=["GET"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])
        self.add_api_route("/set-pressure", self.set_pressure_setpoint, methods=["PUT"])

    async def read_pressure(self, units: str = "bar"):
        """Read from sensor, result to be expressed in units."""
        p = await self.hw_device.get_pressure()
        return p * ureg(units)

    async def set_pressure_setpoint(self, pressure: str) -> bool:
        """Set controlled pressure to the instrument; default unit: bar"""
        await self.hw_device.set_pressure(pressure)
        return True

    async def get_pressure(self) -> float:
        """get current system pressure in bar"""
        return await self.hw_device.get_pressure()

    async def stop(self) -> bool:
        """Stop pressure controller"""
        await self.hw_device.set_pressure("0 bar")
        return True


class MFCComponent(FlowchemComponent):
    hw_device: MFC  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic power supply"""
        super().__init__(name, hw_device)
        self.add_api_route("/get-flow-rate", self.get_flow_setpoint, methods=["GET"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])
        self.add_api_route("/set-flow-rate", self.set_flow_setpoint, methods=["PUT"])

    async def set_flow_setpoint(self, flowrate: str) -> bool:
        """Set flow rate to the instrument; default unit: ml/min"""
        await self.hw_device.set_flow_setpoint(flowrate)
        return True

    async def get_flow_setpoint(self) -> float:
        """get current flow rate in ml/min"""
        return await self.hw_device.get_flow_setpoint()

    async def stop(self) -> bool:
        """Stop mass flow controller"""
        await self.hw_device.set_flow_setpoint("0 ml/min")
        return True
