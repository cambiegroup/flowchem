import time

from loguru import logger
from zeroconf import ServiceBrowser, Zeroconf

from flowchem.client.device_client import FlowchemDeviceClient
from flowchem.client.common import (
    FLOWCHEM_TYPE,
    zeroconf_name_to_device_name,
    device_name_to_zeroconf_name,
    device_url_from_service_info,
    FlowchemCommonDeviceListener,
    flowchem_devices_from_url_dict,
)


class FlowchemDeviceListener(FlowchemCommonDeviceListener):
    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        if service_info := zc.get_service_info(type_, name):
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name):
                self.flowchem_devices[device_name] = url
        else:
            logger.warning(f"No info for service {name}!")


def get_flowchem_device_by_name(
    device_name, timeout: int = 3000
) -> FlowchemDeviceClient | None:
    """
    Given a flowchem device name, search for it via mDNS and return its URL if found.

    Args:
        timeout: timout for search in ms (at least 2 seconds needed)
        device_name: name of the device

    Returns: URL object, empty if not found
    """

    zc = Zeroconf()
    service_info = zc.get_service_info(
        type_=FLOWCHEM_TYPE,
        name=device_name_to_zeroconf_name(device_name),
        timeout=timeout,
    )
    if service_info:
        if url := device_url_from_service_info(service_info, device_name):
            return FlowchemDeviceClient(url)
    return None


def get_all_flowchem_devices(timeout: float = 3000) -> dict[str, FlowchemDeviceClient]:
    """
    Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)
    """
    listener = FlowchemDeviceListener()
    browser = ServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    time.sleep(timeout / 1000)
    browser.cancel()

    return flowchem_devices_from_url_dict(listener.flowchem_devices)


if __name__ == "__main__":
    dev = get_flowchem_device_by_name("test-device")
    print(dev)

    dev_info = get_all_flowchem_devices()
    print(dev_info)
