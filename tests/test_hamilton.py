import sys
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from flowchem.server.api_server import create_server_for_devices
from flowchem.server.configuration_parser import parse_config


@pytest.mark.skipif(sys.platform == "win32", reason="No mock_serial on windows")
@pytest.fixture
def devices(mock_serial) -> dict:
    """ML600 device."""
    mock_serial.stub(receive_bytes=b"aUR\r", send_bytes=b"\x06NV01.01.a")
    mock_serial.stub(receive_bytes=b"1a\r", send_bytes=b"1")
    mock_serial.stub(receive_bytes=b"bUR\r", send_bytes=b"")
    mock_serial.stub(receive_bytes=b":XR\r", send_bytes=b"")

    config = {"device": {}}
    config["device"]["ml600-test"] = {
        "type": "ML600",
        "port": mock_serial.port,
        "syringe_volume": "1 ml",
    }
    return parse_config(config)


@pytest.fixture
async def app(devices) -> FastAPI:
    """ML600-containing app."""
    app = create_server_for_devices(devices)

    # Ugly workaround, essentially startup hooks are not called with AsyncClient
    # See tiangolo/fastapi#2003 for details
    [await dev.initialize() for dev in devices["device"]]

    return app


@pytest.mark.skipif(sys.platform == "win32", reason="No mock_serial on windows")
@pytest.mark.anyio
async def test_root(app):
    """Test root verifies app initialization (config validation/ML600 instantiation)."""
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000") as ac:
        response_root = await ac.get("/")
        response_docs = await ac.get("/docs")
    assert response_root.status_code == 307
    assert response_docs.status_code == 200


@pytest.mark.skipif(sys.platform == "win32", reason="No mock_serial on windows")
@pytest.mark.anyio
async def test_firmware_version(app):
    """Test firmware_version."""
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000/ml600-test") as ac:
        response = await ac.get("/firmware-version")
    assert response.status_code == 200
    assert response.text == '"NV01.01.a"'
