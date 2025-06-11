"""Knauer valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runze_valve import RunzeValve
    from .virtual_runze_valve import VirtualRunzeValve
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

    def __init__(self, name: str, hw_device: RunzeValve | VirtualRunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Update the valve's connections based on the given raw position.

        Parameters:
            raw_position (str | int): The position of the rotor. This can be either a label (e.g., "A") or an index.
            reverse (bool): If True, the direction of the connections will be reversed. Default is False.

        Notes:
            The rotor does not move in a clockwise direction. The critical reference is the position marked
            on the stator of the Valve!
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze8PortDistributionValve(EightPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve | VirtualRunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Update the valve's connections based on the given raw position.

        Parameters:
            raw_position (str | int): The position of the rotor. This can be either a label (e.g., "A") or an index.
            reverse (bool): If True, the direction of the connections will be reversed. Default is False.

        Notes:
            The rotor does not move in a clockwise direction. The critical reference is the position marked
            on the stator of the Valve!
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze10PortDistributionValve(TenPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve | VirtualRunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Update the valve's connections based on the given raw position.

        Parameters:
            raw_position (str | int): The position of the rotor. This can be either a label (e.g., "A") or an index.
            reverse (bool): If True, the direction of the connections will be reversed. Default is False.

        Notes:
            The rotor does not move in a clockwise direction. The critical reference is the position marked
            on the stator of the Valve!
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze12PortDistributionValve(TwelvePortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve | VirtualRunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Update the valve's connections based on the given raw position.

        Parameters:
            raw_position (str | int): The position of the rotor. This can be either a label (e.g., "A") or an index.
            reverse (bool): If True, the direction of the connections will be reversed. Default is False.

        Notes:
            The rotor does not move in a clockwise direction. The critical reference is the position marked
            on the stator of the Valve!
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)


class Runze16PortDistributionValve(SixteenPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve

    def __init__(self, name: str, hw_device: RunzeValve | VirtualRunzeValve) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Update the valve's connections based on the given raw position.

        Parameters:
            raw_position (str | int): The position of the rotor. This can be either a label (e.g., "A") or an index.
            reverse (bool): If True, the direction of the connections will be reversed. Default is False.

        Notes:
            The rotor does not move in a clockwise direction. The critical reference is the position marked
            on the stator of the Valve!
        """
        if reverse:
            return int(raw_position) - 1
        else:
            return int(raw_position) + 1

    async def get_monitor_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str) -> bool:
        """Move valve to position."""
        return await self.hw_device.set_raw_position(position=position)
