""" Autodiscover Knauer devices on network """
import asyncio
import socket
from string import ascii_letters
import random
from typing import Tuple, Union, Text

Address = Tuple[str, int]


class BroadcastProtocol(asyncio.DatagramProtocol):
    """
    From https://gist.github.com/yluthu/4f785d4546057b49b56c
    """

    def __init__(self, target: Address, *, loop: asyncio.AbstractEventLoop = None):
        self.target = target
        self.loop = asyncio.get_event_loop() if loop is None else loop

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")  # type: socket.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast()

    def datagram_received(self, data: Union[bytes, Text], addr: Address):
        print('data received:', data, addr)

    def broadcast(self):
        self.transport.sendto(b"\x00\x01\x00\xf6", self.target)
        # self.loop.call_later(5, self.broadcast)  # Keep sending every 5 secs


def autodiscover_knauer(source_ip: str = "") -> dict:
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
    coro = loop.create_datagram_endpoint(
        lambda: BroadcastProtocol(("255.255.255.255", 30718), loop=loop), local_addr=(source_ip, 28688), )
    loop.run_until_complete(coro)

    print("wait now")
    await asyncio.sleep(5)
    print("waited")
    loop.close()

    return "ok"


if __name__ == '__main__':
    print(autodiscover_knauer("192.168.1.1"))
