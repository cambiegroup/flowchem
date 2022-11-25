"""Control module for the Knauer DAD."""
import asyncio

from loguru import logger

from flowchem.components.analytics.dad import DADControl
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.knauer._common import KnauerEthernetDevice
from flowchem.devices.list_known_device_type import autodiscover_third_party
from flowchem.utils.exceptions import InvalidConfiguration

try:
    from flowchem_knauer import KnauerDADCommands

    HAS_DAD_COMMANDS = True
except ImportError:
    HAS_DAD_COMMANDS = False


class KnauerDAD(KnauerEthernetDevice, FlowchemDevice):
    """DAD control class."""

    def __init__(
        self,
        ip_address=None,
        mac_address=None,
        name: str | None = None,
        turn_on_d2: bool = True,
        turn_on_halogen: bool = True,
    ):
        super().__init__(ip_address, mac_address, name=name)
        self.eol = b"\n\r"
        self._d2 = turn_on_d2
        self._hal = turn_on_halogen
        self._state_d2 = False
        self._state_hal = False

        if not HAS_DAD_COMMANDS:
            raise InvalidConfiguration(
                "You tried to use a Knauer DAD device but the relevant commands are missing!\n"
                "Unfortunately, we cannot publish those as they were provided under NDA.\n"
                "Contact Knauer for further assistance."
            )

        self.cmd = KnauerDADCommands()

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
        self._state_d2 = state
        return await self._send_and_receive(cmd)

    async def hal(self, state: bool = True) -> str:
        """Turn off or on the halogen lamp."""
        cmd = self.cmd.HAL_LAMP_ON if state else self.cmd.HAL_LAMP_OFF
        self._state_hal = state
        return await self._send_and_receive(cmd)

    def components(self):
        return (KnauerDADControl("dad", self),)


class KnauerDADControl(DADControl):
    hw_device: KnauerDAD

    async def get_lamp(self):
        """Lamp status."""
        return {
            "d2": self.hw_device._state_d2,
            "hal": self.hw_device._state_hal,
        }

    async def set_lamp(self, state: bool, lamp_name: str):
        """Lamp status."""
        match lamp_name:
            case "d2":
                await self.hw_device.d2(state)
            case "hal":
                await self.hw_device.hal(state)
            case _:
                logger.error("unknown lamp name!")
