"""Runze valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runze_valve import RunzeValve
from flowchem.components.valves.distribution_valves import (
    SixPortDistributionValve,
    EightPortDistributionValve,
    TenPortDistributionValve,
    TwelvePortDistributionValve,
    SixteenPortDistributionValve,
)


class Runze6PortDistributionValve(SixPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [4, 3, 2, 1, 6, 5]
        if reverse:
            return anti_cc_stator[raw_position]
        else:
            return anti_cc_stator.index(raw_position)

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze8PortDistributionValve(EightPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [5, 4, 3, 2, 1, 8, 7, 6]
        if reverse:
            return anti_cc_stator[raw_position]
        else:
            return anti_cc_stator.index(raw_position)

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze10PortDistributionValve(TenPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [6, 5, 4, 3, 2, 1, 10, 9, 8, 7]
        if reverse:
            return anti_cc_stator[raw_position]
        else:
            return anti_cc_stator.index(raw_position)

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze12PortDistributionValve(TwelvePortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [7, 6, 5, 4, 3, 2, 1, 12, 11, 10, 9, 8]
        if reverse:
            return anti_cc_stator[raw_position]
        else:
            return anti_cc_stator.index(raw_position)

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze16PortDistributionValve(SixteenPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        anti_cc_stator = [9, 8, 7, 6, 5, 4, 3, 2, 1, 16, 15, 14, 13, 12, 11, 10]
        if reverse:
            return anti_cc_stator[raw_position]
        else:
            return anti_cc_stator.index(raw_position)

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)
