from flowchem.client.async_client import (
    async_get_all_flowchem_devices,
)
from flowchem.client.client import get_all_flowchem_devices


def test_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = get_all_flowchem_devices()
    assert "test-device" in dev_dict.keys()


async def test_async_get_all_flowchem_devices(flowchem_test_instance):
    dev_dict = await async_get_all_flowchem_devices()
    assert "test-device" in dev_dict.keys()
