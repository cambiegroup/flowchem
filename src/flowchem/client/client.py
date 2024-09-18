import time

from loguru import logger
from zeroconf import ServiceBrowser, Zeroconf
import socket

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
    Listener for Zeroconf service browser to detect Flowchem devices.

    This listener extends the FlowchemCommonDeviceListener to track Flowchem devices
    discovered through the Zeroconf service. The listener processes services
    by saving device information (name and URL) into the flowchem_devices dictionary.

    Attributes:
        flowchem_devices (dict): Stores the discovered Flowchem devices,
                                 with the device name as the key and the URL as the value.

    Methods:
        _save_device_info(zc: Zeroconf, type_: str, name: str, active_ips: list | None = None) -> None:
            Saves the Flowchem device information if the service info is found.
            Extracts the device URL and saves it into the flowchem_devices dictionary.
    """
    def _save_device_info(self, zc: Zeroconf, type_: str, name: str, active_ips: list | None = None) -> None:
        if service_info := zc.get_service_info(type_, name):
            device_name = zeroconf_name_to_device_name(name)
            if url := device_url_from_service_info(service_info, device_name, active_ips):
                self.flowchem_devices[device_name] = url
        else:
            logger.warning(f"No info for service {name}!")


def get_all_flowchem_devices(timeout: float = 3000, IP_machine: str = "local") -> dict[str, FlowchemDeviceClient]:
    """
    Search for Flowchem devices using Zeroconf and return them as a dictionary.

    This function discovers Flowchem devices using Zeroconf and returns a dictionary
    containing the device names as keys and FlowchemDeviceClient instances as values.

    Args:
        timeout (float, optional): The time to wait (in milliseconds) for devices to be discovered.
                                   Default is 3000 ms (3 seconds).
        IP_machine (str, optional): Specifies the scope of devices to return. If "local",
                                    only devices on the local machine's IP are returned.
                                    If "all", all discovered devices are returned. Otherwise,
                                    a specific IP address can be provided to filter devices
                                    based on that IP.

    Returns:
        dict[str, FlowchemDeviceClient]: A dictionary with Flowchem device names as keys
                                         and FlowchemDeviceClient instances as values,
                                         representing the detected devices.

    Notes:
        - If the IP_machine is set to "local", the function will only return devices
          matching the local machine's IP address.
        - If the IP_machine is a specific IP, only devices on that IP will be included in the result.
        - The function waits for the specified timeout before stopping the search for devices.
    """
    listener = FlowchemDeviceListener()
    browser = ServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    time.sleep(timeout / 1000)
    browser.cancel()

    devices = flowchem_devices_from_url_dict(listener.flowchem_devices)

    if IP_machine == "local":
        ip_target = socket.gethostbyname(socket.gethostname())
    elif IP_machine == "all":
        ...
    else:
        ip_target = IP_machine

    remove_endpoints = []
    for key, endpoint in devices.items():
        if endpoint.url.split(":")[1][2:] != ip_target:
            remove_endpoints.append(key)

    for key in remove_endpoints:
        devices.pop(key)

    return devices


if __name__ == "__main__":
    flowchem_devices: dict[str, FlowchemDeviceClient] = get_all_flowchem_devices()
    for key, endpoint in flowchem_devices.items():
        inf = endpoint.device_info
        msg = f"{key}"
    print(flowchem_devices)
