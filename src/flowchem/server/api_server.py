"""" Run with uvicorn main:app """
from collections.abc import Iterable
from importlib.metadata import metadata
from pathlib import Path

import flowchem
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from flowchem.server.configuration_parser import parse_config_file
from loguru import logger


def create_server_from_file(config_file: Path) -> FastAPI:
    """
    Based on the yaml device config provided, creates connection to devices and API endpoints.

    config: Path to the yaml file with the device config or dict.
    """
    parsed_config = parse_config_file(config_file)
    return create_server_for_devices(parsed_config["device"])


def create_server_for_devices(dev_list: list) -> FastAPI:
    """Initialize and create API endpoints for device object provided."""
    flowchem_metadata = metadata("flowchem")

    # FastAPI server
    app = FastAPI(
        title="flowchem",
        description=flowchem_metadata["Summary"],
        version=flowchem.__version__,
    )

    # Parse list of devices and generate endpoints
    for device in dev_list:
        # Get routers (some compounded devices can return multiple routers for the subcomponents, but most only 1!)
        routers = device.get_router()

        if not isinstance(routers, Iterable):
            routers = (routers,)

        for router in routers:
            # Add to App
            app.include_router(router, tags=router.tags)
            logger.debug(f"Router <{router.prefix}> added to app!")

    # Before server startup intialize all devices
    @app.on_event("startup")
    async def startup_event():
        for device in dev_list:
            await device.initialize()

    return app


if __name__ == "__main__":
    myapp = create_server_from_file(
        config_file=Path(
            "../../../examples/autonomous_reaction_optimization/devices.toml"
        )
    )

    @myapp.get("/", response_class=HTMLResponse, include_in_schema=False)
    def root():
        """Server root"""
        return "<h1>Flowchem Device Server!</h1>" "<a href='./docs/'>API Reference</a>"

    import uvicorn

    uvicorn.run(myapp)
