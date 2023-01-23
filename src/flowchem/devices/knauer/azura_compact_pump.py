"""Azura compact pump component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from ... import ureg

if TYPE_CHECKING:
    from .azura_compact import AzuraCompact
from flowchem.components.pumps.hplc import HPLCPump


def isfloat(rate: str) -> bool:
    try:
        float(rate)
        return True
    except ValueError:
        return False


class AzuraCompactPump(HPLCPump):
    hw_device: AzuraCompact  # for typing's sake

    def __init__(self, name: str, hw_device: AzuraCompact):
        """Initialize component."""
        super().__init__(name, hw_device)

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion."""
        if volume:
            logger.warning(f"Volume parameter ignored: not supported by {self.name}!")

        if isfloat(rate):
            rate = "0 ml/min"
        if rate.isnumeric():
            rate += " ml/min"
            logger.warning("Units missing, assuming ml/min!")

        parsed_rate = ureg.Quantity(rate)

        await self.hw_device.set_flow_rate(rate=parsed_rate)
        return await self.hw_device.infuse()

    async def stop(self) -> bool:
        """Stop pumping."""
        await self.hw_device.stop()
        return True

    async def is_pumping(self) -> bool:
        """Is pump running?"""
        return self.hw_device.is_running()

    @staticmethod
    def is_withdrawing_capable() -> bool:
        """Can the pump reverse its normal flow direction?"""
        return False
