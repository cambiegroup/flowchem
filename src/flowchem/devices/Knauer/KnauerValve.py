"""Knauer valve control."""
import warnings
from enum import Enum

from flowchem.devices.Knauer._common import KnauerEthernetDevice
from flowchem.exceptions import DeviceError
from flowchem.models.injection_valve import InjectionValve
from flowchem.models.multiposition_valve import MultipositionValve
from loguru import logger


class KnauerValveHeads(Enum):
    """
    Four different valve types can be used. 6port2position valve, and 6, 12, 16 multi-position valves
    """

    SIX_PORT_TWO_POSITION = "LI"
    SIX_PORT_SIX_POSITION = "6"
    TWELVE_PORT_TWELVE_POSITION = "12"
    SIXTEEN_PORT_SIXTEEN_POSITION = "16"


class KnauerValve(KnauerEthernetDevice):
    """
    Control Knauer multi position valves.

    Valve type can be 6, 12, 16 or it can be 6 ports, two positions, which will be simply 2 (two states)
    in this case, the response for T is LI. Load and inject can be switched by sending L or I
    maybe valves should have an initial state which is set during init and updated, if no  change don't schedule command
    EN: https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_user-manual_en.pdf
    DE: https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_benutzerhandbuch_de.pdf
    DIP switch for valve selection
    """

    def __init__(self, ip_address=None, mac_address=None, **kwargs):
        super().__init__(ip_address, mac_address, **kwargs)
        self.eol = b"\r\n"
        self.valve_type = None  # Set during initialize()

    async def initialize(self):
        """Initialize connection."""
        # The connection is established in KnauerEthernetDevice.initialize()
        await super().initialize()

        # Detect valve type and state
        self.valve_type = await self.get_valve_type()

    @staticmethod
    def handle_errors(reply: str):
        """True if there are errors, False otherwise. Warns for errors."""

        if not reply.startswith("E"):
            return

        if "E0" in reply:
            DeviceError(
                "The valve refused to switch.\n"
                "Replace the rotor seals of the valve or replace the motor drive unit."
            )
        elif "E1" in reply:
            DeviceError(
                "Skipped switch: motor current too high!\n"
                "Replace the rotor seals of the valve."
            )
        elif "E2" in reply:
            DeviceError(
                "Change from one valve position to the next takes too long.\n"
                "Replace the rotor seals of the valve."
            )
        elif "E3" in reply:
            DeviceError(
                "Switch position of DIP 3 and 4 are not correct.\n"
                "Correct DIP switch 3 and 4."
            )
        elif "E4" in reply:
            DeviceError(
                "Valve homing position not recognized.\n" "Readjust sensor board."
            )
        elif "E5" in reply:
            DeviceError(
                "Switch position of DIP 1 and 2 are not correct.\n"
                "Correct DIP switch 1 and 2."
            )
        elif "E6" in reply:
            DeviceError("Memory error.\n" "Power-cycle valve!")
        else:
            DeviceError("Unspecified error detected!")

    async def _transmit_and_parse_reply(self, message: str) -> str:
        """
        Sends command, receives reply and parse it.

        :param message: str with command to be sent
        :return: reply: str with reply
        """
        reply = await self._send_and_receive(message)
        self.handle_errors(reply)

        if reply == "?":
            # retry once before failing. This happens often on pos commands!
            reply = await self._send_and_receive(message)
            if reply == "?":
                warnings.warn(f"Command failed: {message}")
                logger.warning(f"Command failed: {message}")
                return ""

        return reply

    async def get_position(self) -> str:
        """Return current valve position."""
        return await self._transmit_and_parse_reply("P")

    async def set_position(self, position: str):
        """Move valve to position."""
        position = str(position).upper()
        await self._transmit_and_parse_reply(position)

    async def get_valve_type(self):
        """
        Gets valve type, if returned value is not supported throws an error.

        Note that this method is called during initialize(), therefore it is in line
        with the general philosophy of the module to 'fail early' upon init and avoiding
        raising exception after that.
        """
        reply = await self._transmit_and_parse_reply("T")
        assert reply.startswith("VALVE ")
        reply = reply[6:]

        try:
            headtype = KnauerValveHeads(reply)
        except ValueError as value_error:
            raise DeviceError(
                "The valve type returned is not recognized.\n"
                "Are you sure the address provided is correct?\n"
                "Only multi-pos 6, 12, 16 and 2-pos 6 port valves are supported!"
            ) from value_error

        logger.info(f"Valve connected, type: {headtype}.")
        return headtype


class Knauer6Port2PositionValve(KnauerValve, InjectionValve):
    """KnauerValve of type SIX_PORT_TWO_POSITION."""

    position_mapping = {"LOAD": "L", "INJECT": "I"}

    async def initialize(self):
        """Ensure valve type"""
        await super().initialize()
        assert self.valve_type == KnauerValveHeads.SIX_PORT_TWO_POSITION

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(self.position_mapping[position])

    async def get_position(self) -> str:
        """Move valve to position."""
        valve_pos = await super().get_position()
        return self._reverse_position_mapping[valve_pos]


class Knauer6Port6PositionValve(KnauerValve, MultipositionValve):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    def __init__(
        self, ip_address=None, mac_address=None, default_position: int = 1, name=None
    ):
        super().__init__(
            ip_address=ip_address,
            mac_address=mac_address,
            port_count=6,
            default_position=default_position,
            name=name,
        )

    async def initialize(self):
        """Ensure valve type"""
        await super().initialize()
        assert self.valve_type == KnauerValveHeads.SIX_PORT_SIX_POSITION


class Knauer12PortValve(KnauerValve, MultipositionValve):
    """KnauerValve of type TWELVE_PORT_TWELVE_POSITION."""

    def __init__(
        self, ip_address=None, mac_address=None, default_position: int = 1, name=None
    ):
        super().__init__(
            ip_address=ip_address,
            mac_address=mac_address,
            port_count=12,
            default_position=default_position,
            name=name,
        )

    async def initialize(self):
        """Ensure valve type."""
        await super().initialize()
        assert self.valve_type == KnauerValveHeads.TWELVE_PORT_TWELVE_POSITION


class Knauer16PortValve(KnauerValve, MultipositionValve):
    """KnauerValve of type SIXTEEN_PORT_SIXTEEN_POSITION."""

    def __init__(
        self, ip_address=None, mac_address=None, default_position: int = 1, name=None
    ):
        super().__init__(
            ip_address=ip_address,
            mac_address=mac_address,
            port_count=16,
            default_position=default_position,
            name=name,
        )

    async def initialize(self):
        """Ensure valve type."""
        await super().initialize()
        assert self.valve_type == KnauerValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION


if __name__ == "__main__":
    import asyncio

    v = Knauer6Port6PositionValve(ip_address="192.168.1.176")

    async def main(valve: KnauerValve):
        """test function."""
        await valve.initialize()
        await valve.set_position("I")
        print(await valve.get_position())
        await valve.set_position("L")
        print(await valve.get_position())

    asyncio.run(main(v))
