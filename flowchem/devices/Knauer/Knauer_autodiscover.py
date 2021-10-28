""" Autodiscover Knauer devices on network """
import asyncio
import socket
import time
from queue import Queue, Empty
from threading import Thread
from typing import Tuple, Union, Text, List

from getmac import getmac

Address = Tuple[str, int]


class BroadcastProtocol(asyncio.DatagramProtocol):
    """
    From https://gist.github.com/yluthu/4f785d4546057b49b56c
    """

    def __init__(self, target: Address, response_queue: Queue):
        self.target = target
        self.loop = asyncio.get_event_loop()
        self._queue = response_queue

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")  # type: socket.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast()

    def datagram_received(self, data: Union[bytes, Text], addr: Address):
        self._queue.put(addr[0])

    def broadcast(self):
        self.transport.sendto(b"\x00\x01\x00\xf6", self.target)


async def get_device_type(ip_address: str) -> str:
    """ Returns either 'Pump', 'Valve' or 'Unknown' """
    reader, writer = await asyncio.open_connection(host=ip_address, port=10001)

    # Test Pump
    writer.write("HEADTYPE:?\n\r".encode())
    reply = await reader.readuntil(separator=b"\r")
    if reply.startswith(b"HEADTYPE"):
        return "Pump"

    # Test Valve
    writer.write("T:?\n\r".encode())
    reply = await reader.readuntil(separator=b"\r")
    if reply.startswith(b"VALVE"):
        return "Valve"

    return "Unknown"


def autodiscover_knauer(source_ip: str = "") -> List[Tuple[str, str, None]]:
    """
    Automatically find Knauer ethernet device on the network and returns their data.

    Args:
        source_ip: source IP for autodiscover (only relevant if multiple network interfaces are available!)

    Returns:
        List of tuples (IP, MAC, device_type), one per device replying to autodiscover

    """

    # Define source IP resolving local hostname.
    if not source_ip:
        hostname = socket.gethostname()
        source_ip = socket.gethostbyname(hostname)

    loop = asyncio.get_event_loop()
    device_q = Queue()
    coro = loop.create_datagram_endpoint(
        lambda: BroadcastProtocol(("255.255.255.255", 30718), response_queue=device_q), local_addr=(source_ip, 28688), )
    loop.run_until_complete(coro)
    thread = Thread(target=loop.run_forever)
    thread.start()
    time.sleep(2)
    loop.call_soon_threadsafe(loop.stop)  # here
    thread.join()

    device_list = []
    for _ in range(40):
        try:
            device_list.append(device_q.get_nowait())
        except Empty:
            break

    print(f"The following devices IP have been found: {device_list}")

    device_info = []
    for device_ip in device_list:
        mac = getmac.get_mac_address(ip=device_ip)

        device_type = asyncio.run(get_device_type(device_ip))

        device_info.append((mac, device_ip, device_type))
    return device_info


if __name__ == '__main__':
    autodiscover_knauer()

