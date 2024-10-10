"""Runze valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sy01 import SY01
from flowchem.components.valves.distribution_valves import (
    SixPortDistributionValve,
    NinePortDistributionValve,
    TwelvePortDistributionValve,
)


class SY01_6PortDistributionValve(SixPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: SY01

    def __init__(self, name: str, hw_device: SY01) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [4, 5, 6, 1, 2, 3]
        if reverse:
            return anti_cc_stator.index(raw_position)
        else:
            return anti_cc_stator[raw_position]

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class SY01_9PortDistributionValve(NinePortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: SY01

    def __init__(self, name: str, hw_device: SY01) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [5, 6, 7, 8, 9, 1, 2, 3, 4]
        if reverse:
            return anti_cc_stator.index(raw_position)
        else:
            return anti_cc_stator[raw_position]

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class SY01_12PortDistributionValve(TwelvePortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: SY01

    def __init__(self, name: str, hw_device: SY01) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
        if reverse:
            return anti_cc_stator.index(raw_position)
        else:
            return anti_cc_stator[raw_position]

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)