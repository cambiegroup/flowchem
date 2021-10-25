"""
Module for communication with Knauer pumps and valves.
"""

import logging
import socket
import time

from flowchem import autodiscover_knauer


class KnauerEthernetDevice:
    """
    Common base class for shared logic across Knauer pumps and valves.
    """

    TCP_PORT = 10001
    BUFFER_SIZE = 1024

    def __init__(self, ip_address, port=None, buffersize=None):
        self.ip_address = str(ip_address)
        self.port = int(port) if port else KnauerEthernetDevice.TCP_PORT
        self.buffersize = buffersize if buffersize else KnauerEthernetDevice.BUFFER_SIZE

        self.sock = self._try_connection()
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.DEBUG,
        )

    @classmethod
    def from_mac(cls, mac_address, port=None, buffersize=None):
        """
        Instantiate object from mac address.

        This uses knauer_autodiscover to find the IP of the given MAC address.
        This is desired if a DHCP server is used as the device MAC is fixed,
        unlike its IP address.

        Args:
            mac_address: target MAC address
            port: Optional, port
            buffersize: Optional, buffersize

        Returns:
            a KnauerEthernetDevice object

        """
        # Autodiscover IP from MAC address
        available_devices = autodiscover_knauer()
        # IP if found, None otherwise
        device_ip = available_devices.get(mac_address)

        if device_ip:
            return cls(device_ip, port, buffersize)
        else:
            raise ValueError(f"Device with MAC address={mac_address} not found! [Available: {available_devices}]")

    def __del__(self):
        self.sock.close()

    def _try_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # set timeout to 5s
        sock.settimeout(5)
        try:
            sock.connect((self.ip_address, self.port))
        except socket.timeout:
            logging.error(f"No connection possible to device with IP {self.ip_address}")
            raise ConnectionError(
                f"No Connection possible to device with ip_address {self.ip_address}"
            )

        return sock

    def _send_and_receive(self, message):
        self.sock.send(message.encode())
        time.sleep(0.01)
        reply = ""
        while True:
            chunk = self.sock.recv(self.buffersize).decode()
            reply += chunk
            if "\r" in chunk:
                break
        return reply.strip("\r").rstrip()

    # idea is: try to send message, when reply is received return that. returned reply can be checked against expected
    def _send_and_receive_handler(self, message):
        try:
            reply = self._send_and_receive(message)
        # use other error. if socket ceased to exist, try to reestablish connection. if not possible, raise error
        except socket.timeout:
            try:
                # logger: tell response received, might be good to resend
                # try to reestablish connection, send and receive afterwards
                self.sock = self._try_connection()
                reply = self._send_and_receive(message)
            # no further handling necessary, if this does not work there is a serious problem. Powercycle/check hardware
            except OSError:
                raise ConnectionError(
                    f"Failed to reestablish connection to {self.ip_address}"
                )
        return reply
