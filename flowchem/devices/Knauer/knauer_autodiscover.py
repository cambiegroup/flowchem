from socket import *
import getmac


def autodiscover_knauer(source_ip: str = "192.168.1.1") -> dict:
    # Create a UDP socket
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((source_ip, 28688))
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    sock.settimeout(5)

    server_address = ("255.255.255.255", 30718)
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

    mac_to_ip = {}

    for device_ip in device:
        mac = getmac.get_mac_address(ip=device_ip)
        mac_to_ip[mac] = device_ip
    return mac_to_ip


if __name__ == "__main__":
    devices = autodiscover_knauer()
    print(devices)
    # Currently returns:
    # [('192.168.1.108', '00:80:a3:ce:7e:15'), ('192.168.1.188', '00:80:a3:ba:bf:e2'), ('192.168.1.126', '00:80:a3:ce:8e:43'), ('192.168.1.119', '00:80:a3:b9:0e:33'), ('192.168.1.2', '00:80:a3:90:d5:5e')]
