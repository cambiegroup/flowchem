from loguru import logger

from flowchem.components.valves.distribution_valves import TwoPortDistribution
from flowchem.devices import ML600


class ML600Valve(TwoPortDistribution):
    hw_device: ML600  # for typing's sake

    position_mapping = {
        "input": "9",  # 9 is default inlet, i.e. 1
        "output": "10",  # 10 is default outlet, i.e. 3
    }

    async def set_position(self, position: str) -> bool:
        """Set pump to position."""
        await super().set_position(position)  # Validation
        return await self.hw_device.set_valve_position(
            target_position=ML600Valve.position_mapping[position],
            wait_for_movement_end=True,
        )

    async def get_position(self) -> str:
        """Current pump position."""
        pos = await self.hw_device.get_valve_position()
        reverse_position_mapping = {
            v: k for k, v in ML600Valve.position_mapping.items()
        }
        try:
            return reverse_position_mapping[pos]
        except KeyError:
            logger.error(f"Unknown valve position returned {pos}")
            return ""
