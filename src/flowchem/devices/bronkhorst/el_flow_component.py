from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.base_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .el_flow import MFC


class MFCComponent(FlowchemComponent):
    hw_device: MFC  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic power supply"""
        super().__init__(name, hw_device)
        self.add_api_route("/set-flow-rate", self.get_flow_setpoint, methods=["GET"])
        self.add_api_route("/stop", self.stop, method=["PUT"])
        self.add_api_route("/set-flow-rate", self.set_flow_setpoint, methods=["PUT"])

    async def set_flow_setpoint(self, flowrate: str) -> bool:
        """Set flow rate to the instrument; defaulf unit: ul/min"""
        await self.hw_device.set_flow_setpoint(flowrate)
        return True

    async def get_flow_setpoint(self) -> float:
        """get current flow rate in ml/min"""
        return await self.hw_device.get_flow_setpoint()

    async def stop(self) -> bool:
        """Stop mass flow controller"""
        await self.hw_device.set_flow_setpoint("0 ml/min")
        return True
