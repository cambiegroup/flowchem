from flowchem.client.async_client import (
    async_get_all_flowchem_devices,
    async_get_flowchem_device_by_name,
)
from flowchem.client.client import get_flowchem_device_by_name, get_all_flowchem_devices


def test_get_flowchem_device_url_by_name(flowchem_test_instance):
    dev = get_flowchem_device_by_name("test-device")
    assert "test-device" in str(dev.url)


def test_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = get_all_flowchem_devices()
    assert "test-device" in dev_dict.keys()


async def test_async_get_flowchem_device_by_name(flowchem_test_instance):
    dev = await async_get_flowchem_device_by_name("test-device")
    assert "test-device" in str(dev.url)


async def test_async_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = await async_get_all_flowchem_devices()
    assert "test-device" in dev_dict.keys()
