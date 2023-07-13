import ipaddress

from loguru import logger
from pydantic import AnyHttpUrl
from zeroconf import ServiceInfo, ServiceListener, Zeroconf

from flowchem.client.device_client import FlowchemDeviceClient

FLOWCHEM_SUFFIX = "._labthing._tcp.local."
FLOWCHEM_TYPE = FLOWCHEM_SUFFIX[1:]


def zeroconf_name_to_device_name(zeroconf_name: str) -> str:
    assert zeroconf_name.endswith(FLOWCHEM_SUFFIX)
    return zeroconf_name[: -len(FLOWCHEM_SUFFIX)]


def flowchem_devices_from_url_dict(
    url_dict: dict[str, AnyHttpUrl],
) -> dict[str, FlowchemDeviceClient]:
    dev_dict = {}
    for name, url in url_dict.items():
        dev_dict[name] = FlowchemDeviceClient(url)
    return dev_dict


def device_url_from_service_info(
    service_info: ServiceInfo,
    device_name: str,
) -> AnyHttpUrl | None:
    if service_info.addresses:
        # Needed to convert IP from bytes to str
        device_ip = ipaddress.ip_address(service_info.addresses[0])
        return AnyHttpUrl(f"http://{device_ip}:{service_info.port}/{device_name}")
    logger.warning(f"No address found for {device_name}!")


class FlowchemCommonDeviceListener(ServiceListener):
    def __init__(self) -> None:
        self.flowchem_devices: dict[str, AnyHttpUrl] = {}

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(f"Service {zeroconf_name_to_device_name(name)} removed")
        self.flowchem_devices.pop(name, None)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(f"Service {zeroconf_name_to_device_name(name)} updated")
        self.flowchem_devices.pop(name, None)
        self._save_device_info(zc, type_, name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(f"Service {zeroconf_name_to_device_name(name)} added")
        self._save_device_info(zc, type_, name)

    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        raise NotImplementedError
