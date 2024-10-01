"""Vici valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vici_valve import ViciValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve


class ViciInjectionValve(SixPortTwoPositionValve):
    hw_device: ViciValve  # for typing's sake

    # todo this needs to be adapted to new code
    def _change_connections(self, raw_position: int, reverse: bool = False) -> str:
        raise NotImplementedError("Check that provided mapping is correct")
        # TODO maybe needs addition of one, not sure

        if not reverse: # Is it right?
            translated = raw_position
        else:
            translated = raw_position
        return translated