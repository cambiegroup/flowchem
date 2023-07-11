import ipaddress

from loguru import logger
from zeroconf import ServiceListener, Zeroconf, ServiceInfo

FLOWCHEM_SUFFIX = "._labthing._tcp.local."
FLOWCHEM_TYPE = FLOWCHEM_SUFFIX[1:]


class URL(str):
    def __new__(cls, *value):
        if value:
            v0 = value[0]
            if type(v0) is not str:
                raise TypeError('Unexpected type for URL: "{type(v0)}"')
            if not (v0.startswith("http://") or v0.startswith("https://")):
                raise ValueError('Passed string value "{v0}" is not an "http*://" URL')
        # else allow None to be passed. This allows an "empty" URL instance, e.g. `URL()`
        # `URL()` evaluates False

        return str.__new__(cls, *value)


def zeroconf_name_to_device_name(zeroconf_name: str) -> str:
    assert zeroconf_name.endswith(FLOWCHEM_SUFFIX)
    return zeroconf_name[: -len(FLOWCHEM_SUFFIX)]


def device_name_to_zeroconf_name(device_name: str) -> str:
    return f"{device_name}{FLOWCHEM_SUFFIX}"


def device_url_from_service_info(service_info: ServiceInfo, device_name: str) -> URL:
    if service_info.addresses:
        # Needed to convert IP from bytes to str
        device_ip = ipaddress.ip_address(service_info.addresses[0])
        return URL(f"http://{device_ip}:{service_info.port}/{device_name}")
    else:
        logger.warning(f"No address found for {device_name}!")
        return URL()


class FlowchemCommonDeviceListener(ServiceListener):
    def __init__(self):
        self.flowchem_devices: dict[str, URL] = {}

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
