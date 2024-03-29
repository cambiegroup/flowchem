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
    position_mapping = {"load": "L", "inject": "I"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    async def get_position(self) -> str:
        """Get current valve position."""
        pos = await self.hw_device.get_raw_position()
        assert pos in ("L", "I"), "Valve position is 'I' or 'L'"
        return self._reverse_position_mapping[pos]

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        target_pos = self.position_mapping[position]
        return await self.hw_device.set_raw_position(target_pos)


class Knauer6PortDistributionValve(SixPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)


class Knauer12PortDistributionValve(TwelvePortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)


class Knauer16PortDistributionValve(SixteenPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    async def get_position(self) -> str:
        """Get current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)
