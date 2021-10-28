"""
Module for communication with Knauer pumps and valves.
"""
import asyncio

from flowchem.devices.Knauer.Knauer_autodiscover import autodiscover_knauer
from flowchem.constants import InvalidConfiguration


class KnauerEthernetDevice:
    """
    Common base class for shared logic across Knauer pumps and valves.
    """

    TCP_PORT = 10001
    BUFFER_SIZE = 1024

    def __init__(self, ip_address):
        self.ip_address = str(ip_address)
        self._reader, self._writer = None, None

        # Note: the pump requires "\n\r" as EOL, the valves "\r\n"! So this is set by sublcasses
        self.eol = b""

    @classmethod
    def from_mac(cls, mac_address):
        """
        Instantiate object from mac address.

        This uses knauer_autodiscover to find the IP of the given MAC address.
        This is desired if a DHCP server is used as the device MAC is fixed,
        unlike its IP address.

        Args:
            mac_address: target MAC address
        """
        # Autodiscover IP from MAC address
        available_devices = autodiscover_knauer()
        # IP if found, None otherwise
        device_ip = available_devices.get(mac_address)

        if device_ip:
            return cls(device_ip)
        else:
            raise InvalidConfiguration(f"Device with MAC address={mac_address} not found!\n"
                                       f"[Available: {available_devices}]")

    async def initialize(self):
        """ Initialize connection """
        try:
            self._reader, self._writer = await asyncio.open_connection(host=self.ip_address, port=10001)
        except ConnectionError as e:
            raise InvalidConfiguration(f"Cannot open connection with Knauer Device IP={self.ip_address}") from e

    async def _send_and_receive(self, message):
        self._writer.write(message.encode("ascii")+self.eol)
        reply = await self._reader.readuntil(separator=b"\r")
        return reply.decode("ascii").strip()
