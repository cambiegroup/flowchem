"""VersaPump6 component relative to pumping."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.pumps.syringe_pump import SyringePump

if TYPE_CHECKING:
    from .versapump6 import VersaPump6


class VersaPump6Pump(SyringePump):
    hw_device: VersaPump6  # for typing's sake

    @staticmethod
    def is_withdrawing_capable():
        """ML600 can withdraw."""
        return True

    async def is_pumping(self) -> bool:
        """Check if pump is moving."""
        #return await self.hw_device.is_idle() is False

    async def stop(self):
        """Stop pump."""
        #await self.hw_device.stop()

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion with given rate and volume (both optional).

        """


    async def withdraw(self, rate: str = "1 ml/min", volume: str | None = None) -> bool:
        """Start withdraw with given rate and volume (both optional).

        """

