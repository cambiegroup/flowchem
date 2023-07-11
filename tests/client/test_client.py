from io import BytesIO
from textwrap import dedent

from flowchem.client.async_client import (
    async_get_flowchem_device_by_name,
    async_get_all_flowchem_devices,
)
from flowchem.server.api_server import create_server_from_file


async def test_get_flowchem_device_by_name():
    flowchem_instance = await create_server_from_file(
        BytesIO(
            bytes(
                dedent(
                    """[device.test-device]\n
        type = "FakeDevice"\n"""
                ),
                "utf-8",
            )
        ),
        "0.0.0.0",
    )

    assert flowchem_instance["mdns_server"].server.loop.is_running()
    url = await async_get_flowchem_device_by_name("test-device")
    assert "test-device" in url


async def test_get_all_flowchem_devices():
    flowchem_instance = await create_server_from_file(
        BytesIO(
            bytes(
                dedent(
                    """[device.test-device2]\n
        type = "FakeDevice"\n"""
                ),
                "utf-8",
            )
        ),
        "0.0.0.0",
    )

    assert flowchem_instance["mdns_server"].server.loop.is_running()
    devs = await async_get_all_flowchem_devices()
    print(devs)
    assert "test-device2" in devs.keys()
