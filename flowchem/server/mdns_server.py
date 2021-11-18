""" Creates mDNS server """
import hashlib
import logging
import uuid

# noinspection PyProtectedMember
from zeroconf import IPVersion, ServiceInfo, Zeroconf, get_all_addresses


class Server_mDNS:
    """mDNS server.
    :param host: Host IP address. Defaults to 0.0.0.0.
    :type host: string
    :param port: Host port. Defaults to 7485.
    :type port: int
    :param debug: Enable server debug mode. Defaults to False.
    :type debug: bool
    """

    def __init__(self, host="0.0.0.0", port=7485, debug=False):
        # Server properties
        self.host = host
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

        # Logger
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _get_valid_service_name(name: str):
        """ Given a desired service name, returns a valid one ;) """
        candidate_name = f"{name}._labthing._tcp.local."
        if len(candidate_name) < 64:
            return candidate_name
        else:
            # Hexdigest and not trimming to ensure uniqueness
            return f"{hashlib.sha1(candidate_name.encode()).hexdigest()}._labthing._tcp.local."

    def include_device(self, name, url_prefix):
        """ Adds device to the server. """
        service_name = Server_mDNS._get_valid_service_name(name)

        # LabThing service
        service_info = ServiceInfo(
            type_="_labthing._tcp.local.",
            name=service_name,
            port=self.port,
            properties={
                "path": url_prefix,
                "id": f"{service_name}:{uuid.uuid4()}".replace(" ", ""),
            },
            parsed_addresses=self.mdns_addresses,
        )

        self.server.register_service(service_info)
        self.logger.debug(f"Registered {service_name} on mDNS server!")

    def __del__(self):
        if self.server:
            try:
                self.server.close()
                print("Zeroconf server stopped")
            except TimeoutError:
                pass


if __name__ == "__main__":
    test = Server_mDNS()
    print("ok")
    input()
