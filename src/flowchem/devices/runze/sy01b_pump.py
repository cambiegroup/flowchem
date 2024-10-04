"""Runze component relative to pumping."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from flowchem import ureg
from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.utils.exceptions import DeviceError

if TYPE_CHECKING:
    from .sy01b import SY01B


class SY01BPump(SyringePump):
    pump_code: str
    hw_device: SY01B  # for typing's sake

    def __init__(self, name: str, hw_device: SY01B, pump_code: str = "") -> None:
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
        """Check if pump is moving."""
        status = await self.hw_device.get_motor_status()
        if status == "Motor busy":
            return True
        else:
            return False

    async def stop(self) -> bool:
        """Stop pump."""
        await self.hw_device.force_stop()
        await self.hw_device.wait_until_system_idle()
        return True

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion with given rate and volume (both optional).

        If no rate is specified, the default (1 ml/min) is used, can be set on per-pump basis via `default_infuse_rate`
        If no volume is specified, the max possible volume is infused.
        """
        if await self.is_pumping():
            await self.stop()
        if not rate:
            rate = self.hw_device.config.get("default_infuse_rate")
            logger.warning(f"the flow rate is not provided. set to the default {rate}")
        if not volume:
            target_vol = ureg.Quantity("0 ml")
            logger.warning(f"the volume to infuse is not provided. set to 0 ml")
        else:
            current_volume = await self.hw_device.get_current_volume()
            target_vol = current_volume - ureg.Quantity(volume)
            if target_vol < 0:
                logger.error(
                    f"Cannot infuse target volume {volume}! "
                    f"Only {current_volume} in the syringe!",
                )
                raise DeviceError(f"Cannot infuse target volume {volume}! "
                                  f"Only {current_volume} in the syringe!")

        await self.hw_device.set_syringe_volume(target_vol, ureg.Quantity(rate))
        logger.info(f"infusing is run. it will take {ureg.Quantity(volume) / ureg.Quantity(rate)} to finish.")
        return await self.hw_device.wait_until_system_idle()

    async def withdraw(self, rate: str = "", volume: str | None = None) -> bool:
        """Start withdraw with given rate and volume (both optional).

        If no rate is specified, the default (1 ml/min) is used.
        The default can be set on per-pump basis via `default_withdraw_rate`.
        If no volume is specified, the max possible volume is infused.
        """
        if await self.is_pumping():
            await self.stop()
        if not rate:
            rate = self.hw_device.config["default_withdraw_rate"]
            logger.warning(f"the flow rate is not provided. set to the default {rate}")
        if volume is None:
            target_vol = self.hw_device.syringe_volume
            logger.warning(f"the volume to withdraw is not provided. set to {self.hw_device.syringe_volume}")
        else:
            current_volume = await self.hw_device.get_current_volume()
            target_vol = current_volume + ureg.Quantity(volume)
            if target_vol > self.hw_device.syringe_volume:
                logger.error(
                    f"Cannot withdraw target volume {volume}! "
                    f"Max volume left is {self.hw_device.syringe_volume - current_volume}!",
                )
                raise DeviceError(f"Cannot withdraw target volume {volume}! "
                                  f"Max volume left is {self.hw_device.syringe_volume - current_volume}!")
                # return False

        await self.hw_device.set_syringe_volume(target_vol, ureg.Quantity(rate))
        logger.info(f"withdrawing is run. it will take {ureg.Quantity(volume) / ureg.Quantity(rate)} to finish.")
        return await self.hw_device.wait_until_system_idle()