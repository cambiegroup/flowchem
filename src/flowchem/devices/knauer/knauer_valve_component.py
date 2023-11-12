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


# with new architecture, the only thing that is different is the Injection valve, all other knauer valves have exactly
# the same code -> get additional level of inheritance?

class KnauerInjectionValve(SixPortTwoPositionValve):
    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position, reverse: bool = False):
        position_mapping = {0: "L", 1: "I"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            return position_mapping[raw_position]


class Knauer6PortDistributionValve(SixPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1


class Knauer12PortDistributionValve(TwelvePortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1


class Knauer16PortDistributionValve(SixteenPortDistributionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    def _change_connections(self, raw_position, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1
