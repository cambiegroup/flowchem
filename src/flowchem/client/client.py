import time

from loguru import logger
from pydantic import AnyHttpUrl
from zeroconf import ServiceBrowser, Zeroconf

from flowchem.client.common import (
    FLOWCHEM_TYPE,
    zeroconf_name_to_device_name,
    device_name_to_zeroconf_name,
    device_url_from_service_info,
    FlowchemCommonDeviceListener,
)


class FlowchemDeviceListener(FlowchemCommonDeviceListener):
    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        if service_info := zc.get_service_info(type_, name):
            device_name = zeroconf_name_to_device_name(name)
            self.flowchem_devices[device_name] = device_url_from_service_info(
                service_info, device_name
            )
        else:
            logger.warning(f"No info for service {name}!")


def get_flowchem_device_by_name(device_name, timeout: int = 3000) -> AnyHttpUrl:
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
        return device_url_from_service_info(service_info, device_name)
    else:
        return AnyHttpUrl()


def get_all_flowchem_devices(timeout: float = 3000) -> dict[str, AnyHttpUrl]:
    """
    Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)
    """
    listener = FlowchemDeviceListener()
    browser = ServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    time.sleep(timeout / 1000)
    browser.cancel()

    return listener.flowchem_devices


if __name__ == "__main__":
    url = get_flowchem_device_by_name("test-device")
    print(url)

    dev_info = get_all_flowchem_devices()
    print(dev_info)

    from flowchem.client.common import FlowchemDeviceClient

    for name, url in get_all_flowchem_devices().items():
        dev = FlowchemDeviceClient(url)
        print(dev)
