"""Elite11 pump component."""
from loguru import logger

from .elite11 import Elite11
from flowchem.components.pumps.syringe_pump import SyringePump


class Elite11PumpOnly(SyringePump):
    hw_device: Elite11  # for typing's sake

    @staticmethod
    def is_withdrawing_capable():
        """Elite11 w/o withdraw option."""
        return False

    async def is_pumping(self) -> bool:
        """True if pump is moving."""
        return await self.hw_device.is_moving()

    async def stop(self):
        """Stops pump."""
        await self.hw_device.stop()

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Infuse."""
        if await self.is_pumping():
            logger.warning("Cannot start infusion: pump already moving!")
            return False

        if rate:  # Else previous rate will be used
            await self.hw_device.set_flow_rate(rate)

        if volume:
            await self.hw_device.set_target_volume(volume)

        return await self.hw_device.infuse()


class Elite11PumpWithdraw(Elite11PumpOnly):
    @staticmethod
    def is_withdrawing_capable():
        """Elite11 w/ withdraw option."""
        return True

    async def withdraw(self, rate: str = "1 ml/min", volume: str | None = None) -> bool:
        """Withdraw."""
        if await self.is_pumping():
            logger.warning("Cannot start withdrawing: pump already moving!")
            return False

        if rate:  # Else previous rate will be used
            await self.hw_device.set_withdrawing_flow_rate(rate)

        if volume:  # FIXME check if target volume also works for withdrawing!
            await self.hw_device.set_target_volume(volume)

        return await self.hw_device.withdraw()
