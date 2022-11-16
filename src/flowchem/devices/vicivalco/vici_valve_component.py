"""Vici valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vici_valve import ViciValve
from flowchem.components.valves.injection_valves import SixPortTwoPosition


class ViciInjectionValve(SixPortTwoPosition):
    hw_device: ViciValve  # for typing's sake

    position_mapping = {"load": "1", "inject": "2"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    async def get_position(self) -> str:
        """Get current valve position."""
        pos = await self.hw_device.get_raw_position()
        assert pos in ("1", "2"), "Valve position is '1' or '2'"
        return self._reverse_position_mapping[pos]

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        target_pos = self.position_mapping[position]
        return await self.hw_device.set_raw_position(target_pos)
