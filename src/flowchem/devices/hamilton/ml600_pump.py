"""ML600 component relative to pumping."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.pumps.syringe import SyringePump

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600Pump(SyringePump):
    hw_device: ML600  # for typing's sake

    @staticmethod
    def is_withdrawing_capable():
        """ML600 can withdraw."""
        return True

    async def is_pumping(self) -> bool:
        """True if pump is moving."""
        return await self.hw_device.is_idle() is False

    async def stop(self):
        """Stops pump."""
        await self.hw_device.stop()

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion with given rate and volume (both optional).

        If no rate is specified, the default (1 ml/min) is used, can be set on per-pump basis via `default_infuse_rate`
        If no volume is specified, the max possible volume is infused.
        """
        if not rate:
            rate = self.hw_device.config.get("default_infuse_rate")  # type: ignore

        if not volume:
            target_vol = ureg.Quantity("0 ml")
        else:
            current_volume = await self.hw_device.get_current_volume()
            target_vol = current_volume - ureg.Quantity(volume)
            if target_vol < 0:
                logger.error(
                    f"Cannot infuse target volume {volume}! "
                    f"Only {current_volume} in the syringe!"
                )
                return False

        await self.hw_device.to_volume(target_vol, ureg.Quantity(rate))
        return True

    async def withdraw(self, rate: str = "1 ml/min", volume: str | None = None) -> bool:
        """Start withdraw with given rate and volume (both optional).

        If no rate is specified, the default (1 ml/min) is used.
        The default can be set on per-pump basis via `default_withdraw_rate`.
        If no volume is specified, the max possible volume is infused.
        """
        if not rate:
            rate = self.hw_device.config["default_withdraw_rate"]

        if volume is None:
            target_vol = self.hw_device.syringe_volume
        else:
            current_volume = await self.hw_device.get_current_volume()
            target_vol = current_volume + ureg.Quantity(volume)
            if target_vol > self.hw_device.syringe_volume:
                logger.error(
                    f"Cannot withdraw target volume {volume}! "
                    f"Max volume left is {self.hw_device.syringe_volume - current_volume}!"
                )
                return False

        await self.hw_device.to_volume(target_vol, ureg.Quantity(rate))
        return True
