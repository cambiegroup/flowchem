import asyncio

from loguru import logger
from zeroconf import Zeroconf
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo
from pydantic import AnyHttpUrl

from flowchem.client.client import FlowchemCommonDeviceListener
from flowchem.client.common import (
    FLOWCHEM_TYPE,
    device_name_to_zeroconf_name,
    device_url_from_service_info,
    zeroconf_name_to_device_name,
)


class FlowchemAsyncDeviceListener(FlowchemCommonDeviceListener):
    async def _resolve_service(self, zc: Zeroconf, type_: str, name: str):
        # logger.debug(f"MDNS resolving device '{name}'")
        service_info = AsyncServiceInfo(type_, name)
        await service_info.async_request(zc, 3000)
        if service_info:
            device_name = zeroconf_name_to_device_name(name)
            self.flowchem_devices[device_name] = device_url_from_service_info(
                service_info, device_name
            )
        else:
            logger.warning(f"No info for service {name}!")

    def _save_device_info(self, zc: Zeroconf, type_: str, name: str) -> None:
        asyncio.ensure_future(self._resolve_service(zc, type_, name))


async def async_get_flowchem_device_by_name(
    device_name, timeout: int = 3000
) -> AnyHttpUrl:
    """
    Given a flowchem device name, search for it via mDNS and return its URL if found.

    Args:
        timeout: timout for search in ms (at least 2 seconds needed)
        device_name: name of the device

    Returns: URL object, empty if not found
    """

    zc = AsyncZeroconf()
    service_info = await zc.async_get_service_info(
        type_=FLOWCHEM_TYPE,
        name=device_name_to_zeroconf_name(device_name),
        timeout=timeout,
    )
    if service_info:
        return device_url_from_service_info(service_info, device_name)
    else:
        return AnyHttpUrl()


async def async_get_all_flowchem_devices(
    timeout: float = 3000,
) -> dict[str, AnyHttpUrl]:
    """
    Search for flowchem devices and returns them in a dict (key=name, value=IPv4Address)
    """
    listener = FlowchemAsyncDeviceListener()
    browser = AsyncServiceBrowser(Zeroconf(), FLOWCHEM_TYPE, listener)
    await asyncio.sleep(timeout / 1000)
    await browser.async_cancel()

    return listener.flowchem_devices


if __name__ == "__main__":

    async def main():
        url = await async_get_flowchem_device_by_name("test-device")
        print(url)

        dev_info = await async_get_all_flowchem_devices()
        print(dev_info)

    asyncio.run(main())
