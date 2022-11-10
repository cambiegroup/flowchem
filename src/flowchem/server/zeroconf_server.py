"""Zeroconf (mDNS) server."""
import hashlib
import uuid

from loguru import logger
from zeroconf import get_all_addresses
from zeroconf import IPVersion
from zeroconf import ServiceInfo
from zeroconf import Zeroconf


class ZeroconfServer:
    """ZeroconfServer to advertise FlowchemComponents."""

    def __init__(self, port=8000, debug=False):
        # Server properties
        self.port = port
        self.debug = debug

        self.server = Zeroconf(ip_version=IPVersion.V4Only)

        # Get list of host addresses
        self.mdns_addresses = [
            ip
            for ip in get_all_addresses()  # Get all local IP
            if ip not in ("127.0.0.1", "0.0.0.0")
            and not ip.startswith("169.254")  # Remove invalid IPs
        ]

    @staticmethod
    def _get_valid_service_name(name: str):
        """Given a desired service name, returns a valid one ;)"""
        candidate_name = f"{name}._labthing._tcp.local."
        if len(candidate_name) < 64:
            prefix = name
        else:
            logger.warning(
                f"The device name '{name}' is too long to be used as identifier."
                f"It will be trimmed to "
            )
            # First 30 characters of name + 10 of hash for uniqueness (2^40 ~ 1E12 collision rate is acceptable).
            # The hash is based on the (unique?) name end and limited to 64 i.e. max Blake2b key size
            prefix = (
                name[:30]
                + hashlib.blake2b(
                    key=name[-64:].encode("utf-8"), digest_size=10
                ).hexdigest()
            )

        return f"{prefix}._labthing._tcp.local."

    async def add_component(self, name, url):
        """Adds device to the server."""
        logger.debug(f"Adding zeroconf component {name}")
        service_name = ZeroconfServer._get_valid_service_name(name)

        # LabThing service
        service_info = ServiceInfo(
            type_="_labthing._tcp.local.",
            name=service_name,
            port=self.port,
            properties={
                "path": url,
                "id": f"{service_name}:{uuid.uuid4()}".replace(" ", ""),
            },
            parsed_addresses=self.mdns_addresses,
        )

        await self.server.async_register_service(service_info)
        logger.debug(f"Registered {service_name} on the mDNS server! [ -> {url}]")


if __name__ == "__main__":
    test = ZeroconfServer()
    input()
