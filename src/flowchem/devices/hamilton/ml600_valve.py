"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.valves.valve import Valve
from flowchem.components.valves.distribution_valves import TwoPortDistributionValve

if TYPE_CHECKING:
    from .ml600 import ML600


# class ML600Valve(TwoPortDistributionValve):
#     hw_device: ML600  # for typing's sake
#
#     position_mapping = {
#         "input": "1",  # 9 is default inlet, i.e. 1
#         "output": "3",  # 10 is default outlet, i.e. 3
#     }
#
#     async def set_position(self, position: str) -> bool:
#         """Set pump to position."""
#         await super().set_position(position)  # Validation of the position exist
#         return await self.hw_device.set_valve_position(
#             target_position=ML600Valve.position_mapping[position],
#             wait_for_movement_end=True,
#         )
#
#     async def get_position(self) -> str:
#         """Get current pump position."""
#         pos = await self.hw_device.get_valve_position()
#         reverse_position_mapping = {
#             v: k for k, v in ML600Valve.position_mapping.items()
#         }
#         try:
#             return reverse_position_mapping[pos]
#         except KeyError:
#             logger.error(f"Unknown valve position returned {pos}")
#             return ""

class ML600LeftValve(Valve):
    hw_device: ML600  # for typing's sake
    identifier = "B"
    # angle_mapping = {0: [2, 3], 45: [0, 1], 135: [2, 0], 225: [0, 3], 270: [2, 1]}
    angle_mapping_name = {0: "syr-left", 45: "right-front",
                          135: "syr-front", 225: "left-front",
                          270: "syr-right"}

    def __init__(self, name: str, hw_device: ML600) -> None:
        position_dict = {k + 1: v for k, v in enumerate(self.angle_mapping_name.values())}
        super().__init__(name, hw_device, position_dict, ports=["front", "right", "syr", "left"])

    async def get_position(self) -> str:  # type: ignore
        """Get the current position of the valve."""
        degree = int(await self.hw_device.get_valve_angle(valve_code=self.identifier))
        return self.angle_mapping_name[degree]

    async def set_position(self, position: str) -> bool:
        """Set the valve to the specified position."""
        assert position in self._positions
        reverse_angle_mapping = {
            v: k for k, v in self.angle_mapping_name.items()
        }
        await self.hw_device.set_valve_angle(
            target_angle=reverse_angle_mapping[position],
            valve_code=self.identifier,
            wait_for_movement_end=True,
        )
        return True

class ML600RightValve(Valve):
    hw_device: ML600  # for typing's sake
    identifier = "C"
    angle_mapping = {0: [[2, 3, 0]], 90: [[2, 1], [3, 0]], 180: [[2, 3], [1, 0]], 270: [[2, 1, 0]]}
    angle_mapping_name = {0: "syr-left-front",
                          90: "syr-right&left-front",
                          180: "syr-left&right-front",
                          270: "syr-right-front"}

    def __init__(self, name: str, hw_device: ML600) -> None:
        position_dict = {k + 1: v for k, v in enumerate(self.angle_mapping_name.values())}
        super().__init__(name, hw_device, position_dict, ports=["front", "right", "syr", "left"])

    async def get_position(self) -> str:  # type: ignore
        """Get the current position of the valve."""
        degree = int(await self.hw_device.get_valve_angle(valve_code=self.identifier))
        return self.angle_mapping_name[degree]

    async def set_position(self, position: str) -> bool:
        """Set the valve to the specified position."""
        assert position in self._positions
        reverse_angle_mapping = {
            v: k for k, v in self.angle_mapping_name.items()
        }
        await self.hw_device.set_valve_angle(
            target_angle=reverse_angle_mapping[position],
            valve_code=self.identifier,
            wait_for_movement_end=True,
        )
        return True
