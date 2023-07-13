from flowchem.client.async_client import (
    async_get_all_flowchem_devices,
)
from flowchem.client.client import get_all_flowchem_devices
from flowchem.client.component_client import FlowchemComponentClient
from flowchem.client.device_client import FlowchemDeviceClient


def test_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = get_all_flowchem_devices()
    assert "test-device" in dev_dict

    test_device = dev_dict["test-device"]
    assert isinstance(test_device, FlowchemDeviceClient)
    assert len(test_device.components) == 1

    test_component = test_device["test-component"]
    assert test_component is dev_dict["test-device"]["test-component"]
    assert isinstance(test_component, FlowchemComponentClient)
    assert test_component.component_info.name == "test-component"
    assert test_component.get("test").text == "true"


async def test_async_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = await async_get_all_flowchem_devices()
    assert "test-device" in dev_dict
