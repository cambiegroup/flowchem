""" Autodiscover Knauer devices on network """
import asyncio
import socket
from typing import Tuple

from getmac import getmac

Address = Tuple[str, int]


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


def autodiscover_knauer(source_ip: str = "") -> dict:
    """
    Args:
        source_ip: source IP for autodiscover (only relevant if multiple network interfaces are available!)
    Returns:
        Dictionary of tuples (IP, MAC), one per device replying to autodiscover
    """

    # Define source IP resolving local hostname.
    if not source_ip:
        hostname = socket.gethostname()
        source_ip = socket.gethostbyname(hostname)

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((source_ip, 28688))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)

    server_address = ("255.255.255.255", 30718)
    message = b"\x00\x01\x00\xf6"
    device = []

    try:
        # Send magic autodiscovery UDP packet
        sock.sendto(message, server_address)

        # Receive response
        data = True
        while data:
            try:
                data, server = sock.recvfrom(4096)
            except socket.timeout:
                data = False
            else:
                # Save IP addresses that replied
                device.append(server[0])

    finally:
        sock.close()

    device_info = []

    for device_ip in device:
        mac = getmac.get_mac_address(ip=device_ip)
        device_type = asyncio.run(get_device_type(device_ip))
        device_info.append((mac, device_ip, device_type))
        return device_info




if __name__ == '__main__':
    autodiscover_knauer()

