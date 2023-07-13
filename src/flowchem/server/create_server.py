"""Run with `uvicorn main:app`."""
import asyncio
from io import BytesIO
from pathlib import Path
from typing import TypedDict

from loguru import logger

from flowchem.server.configuration_parser import parse_config
from flowchem.server.zeroconf_server import ZeroconfServer
from flowchem.server.fastapi_server import FastAPIServer


class FlowchemInstance(TypedDict):
    api_server: FastAPIServer
    mdns_server: ZeroconfServer
    port: int


async def create_server_from_file(config_file: BytesIO | Path) -> FlowchemInstance:
    """
    Based on the toml device config provided, initialize connection to devices and create API endpoints.

    config: Path to the toml file with the device config or dict.
    """
    # Parse config (it also creates object instances for all hw dev in config["device"])
    config = parse_config(config_file)

    logger.info("Initializing device connection(s)...")
    # Run `initialize` method of all hw devices in parallel
    await asyncio.gather(*[dev.initialize() for dev in config["device"]])
    logger.info("Device(s) connected")

    return await create_server_for_devices(config)


async def create_server_for_devices(
    config: dict,
) -> FlowchemInstance:
    """Initialize and create API endpoints for device object provided."""
    # mDNS server (Zeroconf)
    mdns = ZeroconfServer(config.get("port", 8000))
    logger.info(f"Zeroconf server up, broadcasting on IPs: {mdns.mdns_addresses}")

    # HTTP server (FastAPI)
    http = FastAPIServer(config.get("filename"))
    logger.debug("HTTP ASGI server app created")

    for device in config["device"]:
        # Advertise devices as services via mDNS
        await mdns.add_device(name=device.name)
        # Add device API to HTTP server
        http.add_device(device)
    logger.info("Server component(s) loaded successfully!")
    return {"api_server": http, "mdns_server": mdns, "port": mdns.port}


if __name__ == "__main__":
    import uvicorn

    async def main():
        flowchem_instance = await create_server_from_file(
            config_file=BytesIO(b"""[device.test-device]\ntype = "FakeDevice"\n""")
        )
        config = uvicorn.Config(
            flowchem_instance["api_server"].app,
            port=flowchem_instance["port"],
            log_level="info",
            timeout_keep_alive=3600,
        )
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
