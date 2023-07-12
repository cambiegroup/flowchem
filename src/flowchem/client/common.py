import ipaddress

import requests
from loguru import logger
from pydantic import AnyHttpUrl
from zeroconf import ServiceListener, Zeroconf, ServiceInfo

from flowchem.components.device_info import DeviceInfo

FLOWCHEM_SUFFIX = "._labthing._tcp.local."
FLOWCHEM_TYPE = FLOWCHEM_SUFFIX[1:]


def zeroconf_name_to_device_name(zeroconf_name: str) -> str:
    assert zeroconf_name.endswith(FLOWCHEM_SUFFIX)
    return zeroconf_name[: -len(FLOWCHEM_SUFFIX)]


def device_name_to_zeroconf_name(device_name: str) -> str:
    return f"{device_name}{FLOWCHEM_SUFFIX}"


def device_url_from_service_info(
    service_info: ServiceInfo, device_name: str
) -> AnyHttpUrl:
    if service_info.addresses:
        # Needed to convert IP from bytes to str
        device_ip = ipaddress.ip_address(service_info.addresses[0])
        return AnyHttpUrl(f"http://{device_ip}:{service_info.port}/{device_name}")
    else:
        logger.warning(f"No address found for {device_name}!")
        return AnyHttpUrl()


class FlowchemCommonDeviceListener(ServiceListener):
    def __init__(self):
        self.flowchem_devices: dict[str, AnyHttpUrl] = {}

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(f"Service {name} removed")
        self.flowchem_devices.pop(name, None)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(f"Service {name} updated")
        self.flowchem_devices.pop(name, None)
        self._save_device_info(zc, type_, name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(f"Service {zeroconf_name_to_device_name(name)} added")
        self._save_device_info(zc, type_, name)

    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        raise NotImplementedError()


class FlowchemDeviceClient:
    def __init__(self, url: AnyHttpUrl):
        self.base_url = url
        self._session = requests.Session()
        # Log every request and always raise for status
        self._session.hooks["response"] = [
            FlowchemDeviceClient.log_responses,
            FlowchemDeviceClient.raise_for_status,
        ]

        # Connect and get device info
        self.info = DeviceInfo.model_validate_json(self.get(url).text)

    @staticmethod
    def raise_for_status(resp, *args, **kwargs):
        resp.raise_for_status()

    @staticmethod
    def log_responses(resp, *args, **kwargs):
        logger.debug(f"Reply: {resp.text} on {resp.url}")

    def get(self, url, **kwargs):
        """Sends a GET request. Returns :class:`Response` object."""
        return self._session.get(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """Sends a POST request. Returns :class:`Response` object."""
        return self._session.post(url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        """Sends a PUT request. Returns :class:`Response` object."""
        return self._session.put(url, data=data, **kwargs)
