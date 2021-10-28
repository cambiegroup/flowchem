""" Autodiscover Knauer devices on network """
import asyncio
import socket
from typing import Tuple, Union, Text, List, Dict

from getmac import getmac

Address = Tuple[str, int]


class BroadcastProtocol(asyncio.DatagramProtocol):
    """
    From https://gist.github.com/yluthu/4f785d4546057b49b56c
    """

    def __init__(self, target: Address, devices: List, *, loop: asyncio.AbstractEventLoop = None):
        self.target = target
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._devices_ip = devices

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")  # type: socket.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_once()

    def datagram_received(self, data: Union[bytes, Text], addr: Address):
        self._devices_ip.append(addr[0])

    def broadcast_once(self):
        self.transport.sendto(b"\x00\x01\x00\xf6", self.target)
        # self.loop.call_later(5, self.broadcast)  # Keep sending every 5 secs


def autodiscover_knauer(source_ip: str = "") -> Dict[str, str]:
    """
    Automatically find Knauer ethernet device on the network and returns their data.

    Args:
        source_ip: source IP for autodiscover (only relevant if multiple network interfaces are available!)

    Returns:
        Dictionary of tuples (IP, MAC), one per device replying to autodiscover

    """

    # Define source IP resolving local hostname.
    if not source_ip:
        hostname = socket.gethostname()
        source_ip = socket.gethostbyname(hostname)

    loop = asyncio.get_event_loop()
    device_list = []
    coro = loop.create_datagram_endpoint(
        lambda: BroadcastProtocol(("255.255.255.255", 30718), devices=device_list), local_addr=(source_ip, 28688), )
    loop.run_until_complete(coro)
    loop.run_until_complete(asyncio.sleep(3))

    mac_to_ip = {}
    for device_ip in device_list:
        mac = getmac.get_mac_address(ip=device_ip)
        mac_to_ip[mac] = device_ip
    return mac_to_ip


if __name__ == '__main__':
    print(autodiscover_knauer("192.168.1.1"))
