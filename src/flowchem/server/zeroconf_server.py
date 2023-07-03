"""Zeroconf (mDNS) server."""
import uuid

from loguru import logger
from zeroconf import get_all_addresses
from zeroconf import IPVersion
from zeroconf import ServiceInfo
from zeroconf import Zeroconf

from flowchem.devices.flowchem_device import DeviceInfo


class ZeroconfServer:
    """ZeroconfServer to advertise FlowchemComponents."""

    def __init__(self, port=8000):
        # Server properties
        self.port = port

        self.server = Zeroconf(ip_version=IPVersion.V4Only)

        # Get list of host addresses
        self.mdns_addresses = [
            ip
            for ip in get_all_addresses()  # Get all local IP
            if ip not in ("127.0.0.1", "0.0.0.0")
            and not ip.startswith("169.254")  # Remove invalid IPs
        ]

    async def add_device(self, name: str, url: str, info: DeviceInfo):
        """Adds device to the server."""
        logger.debug(f"Adding zeroconf component {name}")

        base_info = {
            "path": url,
            "id": f"{name}:{uuid.uuid4()}".replace(" ", ""),
        }
        properites = base_info | dict(info)

        # LabThing service
        service_info = ServiceInfo(
            type_="_labthing._tcp.local.",
            name=name + "._labthing._tcp.local.",
            port=self.port,
            properties=properites,
            parsed_addresses=self.mdns_addresses,
        )

        await self.server.async_register_service(service_info)
        logger.debug(f"Registered {name} on the mDNS server! [ -> {url}]")


if __name__ == "__main__":
    test = ZeroconfServer()
    input()
