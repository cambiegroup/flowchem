"""Knauer valve component."""
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

    hw_device: RunzeValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)

class Runze8PortDistributionValve(EightPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)

class Runze10PortDistributionValve(TenPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)

class Runze12PortDistributionValve(TwelvePortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)


class Runze16PortDistributionValve(SixteenPortDistributionValve):
    """RunzeValve of type SIX_PORT_SIX_POSITION."""

    hw_device: RunzeValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)
