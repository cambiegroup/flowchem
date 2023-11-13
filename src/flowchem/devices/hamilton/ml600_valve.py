"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.valves.distribution_valves import ThreePortTwoPositionValve, ThreePortFourPositionValve

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600LeftValve(ThreePortTwoPositionValve):
    hw_device: ML600  # for typing's sake

    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        raise NotImplementedError("Check that provided mapping is correct")
        if not reverse:
            translated = (raw_position+1) * 135
        else:
            translated = (raw_position/135)-1
        return translated



class ML600GenericValve(ThreePortTwoPositionValve):
    hw_device: ML600  # for typing's sake
    """Use this for a standard one syringe one valve hamilton."""
    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        raise NotImplementedError("Check that provided mapping is correct")
        # TODO no clue which kind of degrees are required on this one - check
        if not reverse:
            translated = (raw_position+1) * 135
        else:
            translated = (raw_position/135)-1
        return translated

class ML600RightValve(ThreePortFourPositionValve):
    hw_device: ML600  # for typing's sake

    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        raise NotImplementedError("Check that provided mapping is correct")
        if not reverse:
            translated = raw_position * 90
        else:
            translated = raw_position/135
        return translated