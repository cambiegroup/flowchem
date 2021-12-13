""" Autodiscover Knauer devices on network """
from typing import Tuple, Union, Text, Dict
import asyncio
import queue
import socket
import sys
import time
from loguru import logger
from threading import Thread

from getmac import getmac

Address = Tuple[str, int]


class BroadcastProtocol(asyncio.DatagramProtocol):
    """From https://gist.github.com/yluthu/4f785d4546057b49b56c"""

    def __init__(self, target: Address, response_queue: queue.Queue):
        self.target = target
        self.loop = asyncio.get_event_loop()
        self._queue = response_queue

    def connection_made(self, transport: asyncio.transports.DatagramTransport):  # type: ignore
        """Called upon connection."""
        sock = transport.get_extra_info("socket")  # type: socket.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # sets to broadcast
        transport.sendto(b"\x00\x01\x00\xf6", self.target)

    def datagram_received(self, data: Union[bytes, Text], addr: Address):
        """Called on data received"""
        logger.trace(f"Received data from {addr}")
        self._queue.put(addr[0])


async def get_device_type(ip_address: str) -> str:
    """Returns either 'Pump', 'Valve' or 'Unknown'"""
    try:
        reader, writer = await asyncio.open_connection(host=ip_address, port=10001)
    except ConnectionError:
        return "ConnectionError"

    # Test Pump
    writer.write("HEADTYPE:?\n\r".encode())
    reply = await reader.readuntil(separator=b"\r")
    if reply.startswith(b"HEADTYPE"):
        logger.debug(f"Device {ip_address} is a Pump")
        return "Pump"

    # Test Valve
    writer.write("T:?\n\r".encode())
    reply = await reader.readuntil(separator=b"\r")
    if reply.startswith(b"VALVE"):
        logger.debug(f"Device {ip_address} is a Valve")
        return "Valve"

    return "Unknown"


def autodiscover_knauer(source_ip: str = "") -> Dict[str, str]:
    """
    Automatically find Knauer ethernet device on the network and returns the IP associated to each MAC address.
    Note that the MAC is the key here as it is the parameter used in configuration files.
    Knauer devices only support DHCP so static IPs are not an option.


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
    device_q: queue.Queue = queue.Queue()
    coro = loop.create_datagram_endpoint(
        lambda: BroadcastProtocol(("255.255.255.255", 30718), response_queue=device_q),
        local_addr=(source_ip, 28688),
    )
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
        except queue.Empty:
            break

    device_info = dict()
    for device_ip in device_list:
        # MAC address
        mac = getmac.get_mac_address(ip=device_ip)
        device_info[mac] = device_ip
    return device_info


if __name__ == "__main__":
    # This is a bug of asyncio on Windows :|
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Autodiscover devices (dict mac as index, IP as value)
    devices = autodiscover_knauer()

    for mac_address, ip in devices.items():
        # Device Type
        device_type = asyncio.run(get_device_type(ip))
        print(f"MAC: {mac_address} IP: {ip} DEVICE_TYPE: {device_type}")
