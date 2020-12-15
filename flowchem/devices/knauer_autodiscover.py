from socket import *
from typing import Tuple, List
import getmac


def autodiscover_knauer(source_ip: str = "192.168.1.1") -> List[Tuple[str, str]]:
    # Create a UDP socket
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((source_ip, 28688))
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    sock.settimeout(5)

    server_address = ('255.255.255.255', 30718)
    message = b"\x00\x01\x00\xf6"
    device = []

    try:
        # Send magic autodiscovery UDP packet
        sent = sock.sendto(message, server_address)

        # Receive response
        data = True
        while data:
            try:
                data, server = sock.recvfrom(4096)
            except timeout:
                data = False

            if data:
                # Save IP addresses that replied
                device.append(server[0])

    finally:
        sock.close()

    mac = [getmac.get_mac_address(ip=device_ip) for device_ip in device]
    return list(zip(device, mac))


if __name__ == '__main__':
    devices = autodiscover_knauer()
    print(devices)
