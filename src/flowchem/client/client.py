import time

from loguru import logger
from zeroconf import ServiceBrowser, Zeroconf

from flowchem.client.common import (
    FLOWCHEM_TYPE,
    FlowchemCommonDeviceListener,
    device_url_from_service_info,
    flowchem_devices_from_url_dict,
    zeroconf_name_to_device_name,
)
from flowchem.client.device_client import FlowchemDeviceClient


class FlowchemDeviceListener(FlowchemCommonDeviceListener):
    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        if service_info := zc.get_service_info(type_, name):
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name):
                self.flowchem_devices[device_name] = url
        else:
            logger.warning(f"No info for service {name}!")


def get_all_flowchem_devices(timeout: float = 3000) -> dict[str, FlowchemDeviceClient]:
    """Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)."""
    listener = FlowchemDeviceListener()
    browser = ServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    time.sleep(timeout / 1000)
    browser.cancel()

    return flowchem_devices_from_url_dict(listener.flowchem_devices)


if __name__ == "__main__":
    dev_info = get_all_flowchem_devices()
    print(dev_info)
