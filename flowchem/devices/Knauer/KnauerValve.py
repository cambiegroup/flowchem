""" Knauer valve control. """

import logging
import warnings
from enum import Enum

from flowchem.constants import DeviceError
from flowchem.devices.Knauer.Knauer_common import KnauerEthernetDevice


class KnauerValveHeads(Enum):
    """
    Four different valve types can be used. 6port2position valve, and 6, 12, 16 multi-position valves
    """

    SIX_PORT_TWO_POSITION = "LI"
    SIX_PORT_SIX_POSITION = 6
    TWELVE_PORT_TWELVE_POSITION = 12
    SIXTEEN_PORT_SIXTEEN_POSITION = 16


class KnauerValve(KnauerEthernetDevice):
    """
    Control Knauer multi position valves.

    Valve type can be 6, 12, 16
    or it can be 6 ports, two positions, which will be simply 2 (two states)
    in this case, the response for T is LI. Load and inject can be switched by sending L or I
    maybe valves should have an initial state which is set during init and updated, if no  change don't schedule command
    EN: https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_user-manual_en.pdf
    DE: https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_benutzerhandbuch_de.pdf
    DIP switch for valve selection
    """

    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.eol = "\r\n"

    async def initialize(self):
        """ Initialize connection """
        # Here the magic happens...
        await super().initialize()

        # Detect valve type and state
        self.valve_type = await self.get_valve_type()
        self._valve_state = await self.get_current_position()

    async def _transmit_and_parse_reply(self, message: str) -> str:
        """
        Sends command, receives reply and parse it.

        :param message: str with command to be sent
        :return: reply: str with reply
        """
        reply = await self._send_and_receive(message)

        if reply == "?":
            # retry once before failing
            reply = await self._send_and_receive(message)
            if reply == "?":
                warnings.warn(f"Command failed: {message}")
                self.logger.warn(f"Command failed: {message}")
                return ""

        try:
            reply = int(reply)
        except ValueError:
            pass
        return reply

    async def get_current_position(self):
        curr_pos = await self._transmit_and_parse_reply("P")
        self.logger.debug(f"Current position is {curr_pos}")
        return curr_pos

    async def switch_to_position(self, position: int or str):
        try:
            position = int(position)
        except ValueError:
            pass

        # allows lower and uppercase commands in case of injection
        if isinstance(position, str):
            position = position.upper()

        # switching necessary?
        if position == self._valve_state:
            logging.debug("already at that position")
            return

        # change to selected position
        reply = await self._transmit_and_parse_reply(position)

        # check if this was done
        if reply == "OK":
            logging.debug("switching successful")
            self._valve_state = position

        elif "E0" in reply:

            logging.error("valve was not switched because valve refused")
            raise DeviceError("valve was not switched because valve refused")

        elif "E1" in reply:
            logging.error("Motor current to high. Check that")
            raise DeviceError("Motor current to high. Check that")

        else:
            raise DeviceError(f"Unknown reply received. Reply is {reply}")

    async def get_valve_type(self):
        """
        Gets valve type, if returned value is not supported throws an error.

        Note that this method is called during initialize(), therefore it is in line
        with the general philosophy of the module to 'fail early' upon init and avoiding
        raising exception after that.
        """
        reply = await self._transmit_and_parse_reply("T")[6:]
        # could be more pretty by passing expected answer to _transmit_and_parse_reply
        try:
            reply = int(reply)
        except ValueError:
            pass
        try:
            headtype = KnauerValveHeads(reply)
        except ValueError as e:
            raise DeviceError(
                f"It seems you're trying instantiate a unknown device/unknown valve type {e} as Knauer Valve."
                "Only Valves of type 16, 12, 10 and LI are supported"
            ) from e
        logging.info(
            f"Valve successfully connected, Type is {headtype} at address {self.ip_address}"
        )
        return headtype


class KnauerAutodetectValve():
    ...

class Knauer6Port2PositionValve():
    ...

class Knauer6Port6PositionValve():
    ...

class Knauer12PortValve():
    ...

class Knauer16PortValve():
    ...


if __name__ == "__main__":
    # This is a bug of asyncio on Windows :|
    import sys
    import asyncio

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    v = KnauerValve(ip_address="192.168.1.176")

    async def main(valve: KnauerValve):
        await valve.initialize()

    asyncio.run(main(v))
