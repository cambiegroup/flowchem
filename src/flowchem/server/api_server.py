"""Run with `uvicorn main:app`."""
import asyncio
from importlib.metadata import metadata
from io import BytesIO
from pathlib import Path
from typing import TypedDict, Iterable

from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from loguru import logger
from starlette.responses import RedirectResponse

import flowchem
from flowchem.devices.flowchem_device import RepeatedTaskInfo
from flowchem.server.configuration_parser import parse_config
from flowchem.server.zeroconf_server import ZeroconfServer


class FlowchemInstance(TypedDict):
    api_server: FastAPI
    mdns_server: ZeroconfServer
    port: int


async def run_create_server_from_file(
    config_file: BytesIO | Path, host: str = "127.0.0.1"
) -> FlowchemInstance:
    """Make create_server_from_file a sync function for CLI."""

    return await create_server_from_file(config_file, host)


async def create_server_from_file(
    config_file: BytesIO | Path, host: str
) -> FlowchemInstance:
    """
    Based on the toml device config provided, initialize connection to devices and create API endpoints.

    config: Path to the toml file with the device config or dict.
    """
    # Parse config (it also creates object instances for all hw dev in config["device"])
    config = parse_config(config_file)

    logger.info("Initializing devices...")
    # Run `initialize` method of all hw devices in parallel
    await asyncio.gather(*[dev.initialize() for dev in config["device"]])
    # Collect background repeated tasks for each device (will need to schedule+start these)
    bg_tasks = [dev.repeated_task() for dev in config["device"] if dev.repeated_task()]
    logger.info("Device initialization complete!")

    return await create_server_for_devices(config, bg_tasks, host)


async def create_server_for_devices(
    config: dict,
    repeated_tasks: Iterable[RepeatedTaskInfo] = (),
    host: str = "127.0.0.1",
) -> FlowchemInstance:
    """Initialize and create API endpoints for device object provided."""
    dev_list = config["device"]
    port = config.get("port", 8000)

    # HTTP server (FastAPI)
    app = FastAPI(
        title=f"Flowchem - {config.get('filename')}",
        description=metadata("flowchem")["Summary"],
        version=flowchem.__version__,
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # mDNS server (Zeroconfig)
    mdns = ZeroconfServer(port=port)
    api_base_url = r"http://" + f"{host}:{port}"

    for seconds_delay, task_to_repeat in repeated_tasks:

        @app.on_event("startup")
        @repeat_every(seconds=seconds_delay)
        async def my_task():
            logger.debug("Running repeated task...")
            await task_to_repeat()

    @app.route("/")
    def home_redirect_to_docs(root_path):
        """Redirect root to `/docs` to enable interaction w/ API."""
        return RedirectResponse(url="/docs")

    # For each device get the relevant APIRouter(s) and add them to the app
    for device in dev_list:
        # Get components (some compounded devices can return multiple components)
        components = device.components()
        device.get_metadata()
        logger.debug(f"Got {len(components)} components from {device.name}")

        # Advertise devices (not components!)
        await mdns.add_device(name=device.name, url=api_base_url)

        for component in components:
            # API endpoints registration
            app.include_router(component.router, tags=component.router.tags)
            logger.debug(f"Router <{component.router.prefix}> added to app!")

    return {"api_server": app, "mdns_server": mdns, "port": port}


if __name__ == "__main__":
    import io
    import uvicorn

    async def main():
        flowchem_instance = await run_create_server_from_file(
            config_file=io.BytesIO(
                b"""[device.test-device]\n
        type = "FakeDevice"\n"""
            )
        )
        config = uvicorn.Config(
            flowchem_instance["api_server"],
            port=flowchem_instance["port"],
            log_level="info",
            timeout_keep_alive=3600,
        )
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
