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
    """
    creat
    """
    def _save_device_info(self, zc: Zeroconf, type_: str, name: str, active_ips: list) -> None:
        """

        Args:
            zc:
            type_: '_labthing._tcp.local.'
            name: 'device._labthing._tcp.local.'

        Returns:

        """
        zc_info = zc.get_service_info(type_, name)
        # ServiceInfo(type='_labthing._tcp.local.', name='pressMFC._labthing._tcp.local.',
        # addresses=[b'\xc0\xa8\x01\x01', b'\xc0\xa8\x017', b'\xc0\xa8\nk', b'\x8d\x0e4\xd2'], all store address will be saved
        # port=8000, weight=0, priority=0, server='pressMFC._labthing._tcp.local.',
        # properties={b'id': b'pressMFC:020cbe77-03d0-44a6-a018-93dc28c0c097', b'path': b'http://192.168.1.55:8000/pressMFC/'}, interface_index=None)
        if service_info := zc.get_service_info(type_, name):
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name, active_ips):
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
    flowchem_devices: dict[str, FlowchemDeviceClient] = get_all_flowchem_devices()
    print(flowchem_devices)
