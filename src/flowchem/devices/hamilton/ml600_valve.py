"""ML600 component relative to valve switching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.valves.distribution_valves import ThreePortTwoPositionValve, ThreePortFourPositionValve, FourPortFivePositionValve

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600LeftValve(FourPortFivePositionValve):
    hw_device: ML600  # for typing's sake
    identifier = "B"
    # 0 degree syr-left, 
    # 45 right-front
    # 90 nothing
    # 135 front-syr
    # 180
    # 225 left front
    # 270 syr-right
    # 315
    # 360
    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        if not reverse:
            translated = (raw_position) * 45
        else:
            translated = round(raw_position/45)
        return translated


class ML600GenericValve(ThreePortTwoPositionValve):
    hw_device: ML600  # for typing's sake
    identifier = ""
    """Use this for a standard one syringe one valve hamilton."""
    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        # TODO no clue which kind of degrees are required on this one - check
        if not reverse:
            translated = (raw_position+1) * 135
        else:
            translated = (raw_position/135)-1
        return translated

class ML600RightValve(ThreePortFourPositionValve):
    hw_device: ML600  # for typing's sake
    identifier = "C"
    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        if not reverse:
            translated = raw_position * 90
        else:
            translated = raw_position/135
        return translated