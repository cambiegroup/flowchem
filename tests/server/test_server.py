from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from flowchem.server.api_server import create_server_from_file


@pytest.fixture(scope="function")
def app():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("test_configuration.toml", "w") as f:
            f.write(
                dedent(
                    """[device.test-device]\n
                    type = "FakeDevice"\n"""
                )
            )
        yield create_server_from_file(Path("test_configuration.toml"))


def test_read_main(app):
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Flowchem" in response.text

    response = client.get("/test-device/test")
    assert response.status_code == 200
    assert response.text == "true"

    response = client.get("/test-device2")
    assert response.status_code == 404
