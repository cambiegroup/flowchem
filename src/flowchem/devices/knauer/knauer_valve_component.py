"""Knauer valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .knauer_valve import KnauerValve
from flowchem.components.valves.distribution_valves import (
    SixPortDistributionValve,
    SixteenPortDistributionValve,
    TwelvePortDistributionValve,
)
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve


class KnauerInjectionValve(SixPortTwoPositionValve):
    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """Create a ValveControl object."""
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str, reverse: bool = False):
        position_mapping = {0: "L", 1: "I"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            return position_mapping[raw_position]

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        position_mapping = {"load": "L", "inject": "I"}
        _reverse_position_mapping = {v: k for k, v in position_mapping.items()}
        pos = await self.hw_device.get_raw_position()
        assert pos in ("L", "I"), "Valve position is 'I' or 'L'"
        return _reverse_position_mapping[pos]

    async def set_monitor_position(self, position: str):
        """Move valve to position."""
        position_mapping = {"load": "L", "inject": "I"}
        target_pos = position_mapping[position]
        return await self.hw_device.set_raw_position(target_pos)

class Knauer6PortDistributionValve(SixPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position: int, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1


class Knauer12PortDistributionValve(TwelvePortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position:int, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1


class Knauer16PortDistributionValve(SixteenPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position:int, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1
