from io import BytesIO

from flowchem.client.async_client import (
    _async_get_all_flowchem_devices_url,
    _async_get_flowchem_device_url_by_name,
)
from flowchem.server.create_server import create_server_from_file


async def test_get_flowchem_device_url_by_name():
    flowchem_instance = await create_server_from_file(
        BytesIO(
            bytes(
                """[device.test-device]\ntype = "FakeDevice"\n""",
                "utf-8",
            )
        )
    )

    assert flowchem_instance["mdns_server"].server.loop.is_running()
    url = await _async_get_flowchem_device_url_by_name("test-device")
    assert "test-device" in str(url)


async def test_get_all_flowchem_devices_url():
    flowchem_instance = await create_server_from_file(
        BytesIO(
            bytes(
                """[device.test-device2]\ntype = "FakeDevice"\n""",
                "utf-8",
            )
        )
    )

    assert flowchem_instance["mdns_server"].server.loop.is_running()
    devs = await _async_get_all_flowchem_devices_url()
    print(devs)
    assert "test-device2" in devs.keys()
