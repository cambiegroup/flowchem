"""ML600 component relative to pumping."""
from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.pumps.syringe_pump import SyringePump

if TYPE_CHECKING:
    from .ml600 import ML600


class ML600Pump(SyringePump):
    hw_device: ML600  # for typing's sake

    def __init__(self, name: str, hw_device: ML600, pump_code: str = "") -> None:
        """
        Create a Pump object.
        "" for single syringe pump. B or C  for dual syringe pump.
        """
        super().__init__(name, hw_device)
        self.pump_code = pump_code
        # self.add_api_route("/pump", self.get_monitor_position, methods=["GET"])

    @staticmethod
    def is_withdrawing_capable() -> bool:
        """ML600 can withdraw."""
        return True

    async def is_pumping(self) -> bool:
        """Check if pump is moving. this is not specific for pump but for whole devices"""
        return await self.hw_device.get_pump_status()

    async def stop(self) -> bool:
        """Stop pump."""
        return await self.hw_device.stop(self.pump_code)

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
            current_volume = await self.hw_device.get_current_volume(self.pump_code)
            target_vol = current_volume - ureg.Quantity(volume)
            if target_vol < 0:
                logger.error(
                    f"Cannot infuse target volume {volume}! "
                    f"Only {current_volume} in the syringe!",
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
                    f"Max volume left is {self.hw_device.syringe_volume - current_volume}!",
                )
                return False

        await self.hw_device.to_volume(target_vol, ureg.Quantity(rate), self.pump_code)
        return True
