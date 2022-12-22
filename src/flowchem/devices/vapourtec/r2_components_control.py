""" Control module for the Vapourtec R2 valves """
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.valves.injection_valves import SixPortTwoPosition
from flowchem.components.valves.distribution_valves import TwoPortDistribution
from flowchem.components.pumps.hplc import HPLCPump
if TYPE_CHECKING:
    from .r2 import R2
    from .r4_heater import R4Heater


class R2InjectionValve(SixPortTwoPosition): #total 2 injection loop (A, B)
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    position_mapping = {"load": "1", "inject": "2"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    def __init__(self, name: str, hw_device: R2, channel: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.channel = channel

    async def get_position(self) -> str:
        """Get current valve position."""
        self.hw_device.last_state.valve[self.valve_number]



    async def set_position(self, position: str):
        """Move valve to position."""







class R2TwoPortValve(TwoPortDistribution): #total 3 valve (A, B, Collection)
    """R2 reactor injection loop valve control class."""

    hw_device: R2  # for typing's sake

    position_mapping = {"load": "1", "inject": "2"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    def __init__(self, name: str, hw_device: R2, channel: int):
        """Create a ValveControl object."""
        super().__init__(name, hw_device)
        self.channel = channel

    async def get_position(self) -> str:
        """Get current valve position."""
        self.hw_device.last_state.valve[self.valve_number]



    async def set_position(self, position: str):
        """Move valve to position."""


class R2HPLCPump(HPLCPump):




class R4

