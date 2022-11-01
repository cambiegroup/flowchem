"""Control module for the Knauer DAD."""
import asyncio

from loguru import logger

from flowchem.devices.list_known_device_type import autodiscover_third_party
from flowchem.exceptions import InvalidConfiguration
from flowchem.models.analytical_device import AnalyticalDevice


class KnauerDAD(KnauerEthernetDevice, AnalyticalDevice):
    """DAD control class."""

    def __init__(
        self,
        ip_address=None,
        mac_address=None,
        name: str | None = None,
        turn_on_d2: bool = True,
        turn_on_halogen: bool = True,
        **config
    ):
        super().__init__(ip_address, mac_address, name=name)
        self.eol = b"\n\r"
        self._d2 = turn_on_d2
        self._hal = turn_on_halogen

        plugins = autodiscover_third_party()
        if not "KnauerDADCommands" in plugins:
            raise InvalidConfiguration(
                "You tried to use a Knauer DAD device but the relevant commands are missing!\n"
                "Unfortunately, we cannot publish those as they were provided under NDA.\n"
                "Contact Knauer for further assistance."
            )
        self.cmd = plugins["KnauerDADCommands"]

    async def initialize(self):
        """Initialize connection."""
        await super().initialize()

        if self._d2:
            await self.d2(True)
            await asyncio.sleep(1)
        if self._hal:
            await self.hal(True)
            await asyncio.sleep(15)

    async def d2(self, state: bool = True) -> str:
        """Turn off or on the deuterium lamp."""
        cmd = self.cmd.D2_LAMP_ON if state else self.cmd.D2_LAMP_OFF
        return await self._send_and_receive(cmd)

    async def hal(self, state: bool = True) -> str:
        """Turn off or on the halogen lamp."""
        cmd = self.cmd.HAL_LAMP_ON if state else self.cmd.HAL_LAMP_OFF
        return await self._send_and_receive(cmd)

    def get_router(self, prefix: str | None = None):
        """Create an APIRouter for this object."""
        router = super().get_router()
        router.add_api_route("/deuterium-lamp", self.d2, methods=["PUT"])
        router.add_api_route("/halogen-lamp", self.hal, methods=["PUT"])
        return router
