"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.valves.distribution_valves import EightPortDistributionValve

if TYPE_CHECKING:
    from .versapump6 import VersaPump6


class VersaPump6Valve(EightPortDistributionValve):
    hw_device: VersaPump6  # for typing's sake

    position_mapping = {
        "input": "1",  # 9 is default inlet, i.e. 1
        "output": "3",  # 10 is default outlet, i.e. 3
    }

    async def set_position(self, position: str) -> bool:
        """Set pump to position."""
        await super().set_position(position)  # Validation
        return await self.hw_device.set_valve_position(
            target_position=VersaPump6Valve.position_mapping[position],
            wait_for_movement_end=True,
        )

    async def get_position(self) -> str:
        """Get current pump position."""
        pos = await self.hw_device.get_valve_position()
        reverse_position_mapping = {
            v: k for k, v in VersaPump6Valve.position_mapping.items()
        }
        try:
            return reverse_position_mapping[pos]
        except KeyError:
            logger.error(f"Unknown valve position returned {pos}")
            return ""
