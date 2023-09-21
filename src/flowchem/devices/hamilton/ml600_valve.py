"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.valves.distribution_valves import TwoPortDistribution

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600Valve(TwoPortDistribution):
    hw_device: ML600  # for typing's sake

    # position_mapping = {
    #     "input": "1",  # 9 is default inlet, i.e. 1
    #     "output": "3",  # 10 is default outlet, i.e. 3
    # }
    def __init__(self, name: str, hw_device: ML600, valve_code: str = ""):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.valve_code = valve_code   #"left:B, right:C"

    async def set_position(self, position: str) -> bool:
        """Set pump to position."""
        # await super().set_position(position)  # Validation
        return await self.hw_device.set_valve_position(
            target_position=ML600Valve.position_mapping[position],
            valve_code=self.valve_code,
            wait_for_movement_end=True,

        )

    async def get_position(self) -> str:
        """Current pump position."""
        pos = await self.hw_device.get_valve_position(valve_code=self.valve_code,)
        reverse_position_mapping = {
            v: k for k, v in ML600Valve.position_mapping.items()
        }
        try:
            return reverse_position_mapping[pos]
        except KeyError:
            logger.error(f"Unknown valve position returned {pos}")
            return ""
