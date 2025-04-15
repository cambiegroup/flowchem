from flowchem.devices.harvardapparatus.elite11_pump import Elite11PumpWithdraw
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import samuel_saraiva
from loguru import logger


class VirtualElite11(FlowchemDevice):
    """Virtual Elite11 class to simulate the behavior of the real Harvard Apparatus Elite 11 syringe pump."""

    def __init__(self, name: str = "", **kwargs) -> None:

        # Call the parent class constructor with the virtual HarvardApparatusPumpIO
        super().__init__(name)

        # Override device info for virtual device
        self.device_info.authors=[samuel_saraiva]
        self.device_info.manufacturer="Virtual Harvard Apparatus"
        self.device_info.model="Virtual Elite 11"

    @classmethod
    def from_config(cls, **kwargs):
        return cls(**kwargs)

    async def initialize(self):
        self.components.append(Elite11PumpWithdraw("pump", self)) # type: ignore

    async def is_moving(self) -> bool:
        return False

    async def set_flow_rate(self, rate: str):
        logger.info(f"Set infuse flow rate {rate}")

    async def set_target_volume(self, volume: str):
        logger.info(f"Set traget volume: {volume}")

    async def infuse(self):
        return True

    async def withdraw(self):
        return True

    async def set_withdrawing_flow_rate(self, rate: str):
        logger.info(f"Set withdraw flow rate {rate}")

    async def stop(self):
        return True