"""
Module for communication with Knauer pumps and valves.
"""
import asyncio
import logging
from asyncio import StreamReader, StreamWriter

from flowchem.components.devices.Knauer.Knauer_autodiscover import autodiscover_knauer
from flowchem.exceptions import InvalidConfiguration


class KnauerEthernetDevice:
    """
    Common base class for shared logic across Knauer pumps and valves.
    """

    TCP_PORT = 10001
    BUFFER_SIZE = 1024
    _id_counter = 0

    def __init__(self, ip_address, mac_address, name: str = None):
        """
        Knauer Ethernet Device - either pump or valve.

        If a MAC address is given, it is used to autodiscover the IP address.
        Otherwise, the IP address must be given.

        Note that for configuration files, the MAC address is preferred as it is static.

        Args:
            ip_address: IP address of Knauer device
            mac_address: MAC address of Knauer device
            name: name of device (optional)
        """
        # This is actually a copy of the code in Component() because multiple inheritance of childern
        # That is, inheriting both from KnauerEthernetDevice and Pump/Valve makes it hard to call Component.__init__()
        if name is None:
            self.name = self.__class__.__name__ + "_" + str(self.__class__._id_counter)
            self.__class__._id_counter += 1
        else:
            self.name = str(name)

        # MAC address
        if mac_address:
            self.ip_address = self._ip_from_mac(mac_address)
        else:
            self.ip_address = ip_address

        # Logger
        self.logger = (
            logging.getLogger(__name__)
            .getChild(self.__class__.__name__)
            .getChild(self.name)
        )

        # These will be set in initialize()
        self._reader: StreamReader = None  # type: ignore
        self._writer: StreamWriter = None  # type: ignore

        # Note: the pump requires "\n\r" as EOL, the valves "\r\n"! So this is set by sublcasses
        self.eol = b""

    def _ip_from_mac(self, mac_address: str) -> str:
        """ Gets IP from MAC. """
        # Autodiscover IP from MAC address
        available_devices = autodiscover_knauer()
        # IP if found, None otherwise
        ip_address = available_devices.get(mac_address)
        if ip_address is None:
            raise InvalidConfiguration(
                f"Device with MAC address={mac_address} not found!\n"
                f"[Available: {available_devices}]"
            )
        return ip_address

    async def initialize(self):
        """ Initialize connection """
        try:
            self._reader, self._writer = await asyncio.open_connection(
                host=self.ip_address, port=10001
            )
        except ConnectionError as e:
            raise InvalidConfiguration(
                f"Cannot open connection with Knauer Device IP={self.ip_address}"
            ) from e

    async def _send_and_receive(self, message: str) -> str:
        self._writer.write(message.encode("ascii") + self.eol)
        self.logger.debug(f"WRITE >>> '{message}' ")
        reply = await self._reader.readuntil(separator=b"\r")
        self.logger.debug(f"READ <<< '{reply.decode().strip()}' ")
        return reply.decode("ascii").strip()
