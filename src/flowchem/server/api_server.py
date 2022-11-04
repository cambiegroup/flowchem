"""Run with `uvicorn main:app`."""
import asyncio
from importlib.metadata import metadata
from pathlib import Path
from typing import BinaryIO
from typing import TypedDict

from fastapi import FastAPI
from loguru import logger
from starlette.responses import RedirectResponse

import flowchem
from flowchem.server.configuration_parser import parse_config
from flowchem.server.zeroconf_server import ZeroconfServer


class FlowchemInstance(TypedDict):
    api_server: FastAPI
    mdns_server: ZeroconfServer
    port: int


def run_create_server_from_file(
    config_file: BinaryIO | Path, host: str = "127.0.0.1"
) -> FlowchemInstance:
    """Make create_server_from_file a sync function for CLI."""

    return asyncio.run(create_server_from_file(config_file, host))


async def create_server_from_file(
    config_file: BinaryIO | Path, host: str
) -> FlowchemInstance:
    """
    Based on the toml device config provided, initialize connection to devices and create API endpoints.

    config: Path to the toml file with the device config or dict.
    """
    # Parse config create object instances for all hw devices
    parsed_config = parse_config(config_file)

    # Run `initialize` method of all hw devices
    await asyncio.gather(*[dev.initialize() for dev in parsed_config["device"]])

    return await create_server_for_devices(parsed_config, host)


async def create_server_for_devices(config: dict, host) -> FlowchemInstance:
    """Initialize and create API endpoints for device object provided."""
    dev_list = config["device"]
    port = config.get("port", 8000)

    # FastAPI server
    app = FastAPI(
        title=f"Flowchem - {config.get('filename')}",
        description=metadata("flowchem")["Summary"],
        version=flowchem.__version__,
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    mdns = ZeroconfServer(port=port, debug=False)
    api_base_url = r"http://" + f"{host}:{port}"

    @app.route("/")
    def home_redirect_to_docs(root_path):
        """Redirect root to `/docs` to enable interaction w/ API."""
        return RedirectResponse(url="/docs")

    # For each device get the relevant APIRouter(s) and add them to the app
    for device in dev_list:
        # Get components (some compounded devices can return multiple components)
        components = device.components()

        for component in components:
            # API endpoints registration
            app.include_router(component.router, tags=component.router.tags)
            logger.debug(f"Router <{component.router.prefix}> added to app!")

            # Advertise component via zeroconfig
            await mdns.add_component(
                name=component.name, url=api_base_url + component.router.prefix
            )

    return {"api_server": app, "mdns_server": mdns, "port": port}


if __name__ == "__main__":
    import io

    test_conf = io.BytesIO(
        b"""[device.test-device]\n
    type = "FakeDevice"\n"""
    )
    flowchem_instance = run_create_server_from_file(config_file=test_conf)

    import uvicorn

    uvicorn.run(flowchem_instance["api_server"])
