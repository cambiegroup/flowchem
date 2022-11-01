"""Run with `uvicorn main:app`."""
from collections.abc import Iterable
from importlib.metadata import metadata
from pathlib import Path

from fastapi import FastAPI
from loguru import logger
from starlette.responses import RedirectResponse

import flowchem
from flowchem.exceptions import InvalidConfiguration
from flowchem.server.configuration_parser import parse_config_file


def create_server_from_file(config_file: Path) -> FastAPI:
    """
    Based on the yaml device config provided, creates connection to devices and API endpoints.

    config: Path to the yaml file with the device config or dict.
    """
    parsed_config = parse_config_file(config_file)
    return create_server_for_devices(parsed_config)


def create_server_for_devices(config: dict) -> FastAPI:
    """Initialize and create API endpoints for device object provided."""
    flowchem_metadata = metadata("flowchem")
    dev_list = config["device"]

    # FastAPI server
    app = FastAPI(
        title=f"Flowchem - {config.get('filename')}",
        description=flowchem_metadata["Summary"],
        version=flowchem.__version__,
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    @app.route("/")
    def home_redirect_to_docs(root_path):
        """Redirect root to `/docs` to enable interaction w/ API."""
        return RedirectResponse(url="/docs")

    # For each device get the relevant APIRouter(s) and add them to the app
    for device in dev_list:
        # Get routers (some compounded devices can return multiple routers for the subcomponents, but most only 1!)
        routers = device.get_router()

        if not isinstance(routers, Iterable):
            routers = (routers,)

        for router in routers:
            if (
                router is None
            ):  # Common mistake on method subclassing, let's provide a useful message ;)
                logger.error(
                    f"The device {device} did not return a valid APIRouter from its `get_router()` method!"
                )
                raise InvalidConfiguration(f"{device}.get_router() returned None!")

            app.include_router(router, tags=router.tags)
            logger.debug(f"Router <{router.prefix}> added to app!")

    @app.on_event("startup")
    async def startup_event():
        """Call all device initialize async methods upon startup."""
        [await dev.initialize() for dev in dev_list]
        logger.info(f"Device initialization completed, server ready!")

    return app


if __name__ == "__main__":
    test_conf = Path("../../../examples/autonomous_reaction_optimization/devices.toml")
    myapp = create_server_from_file(config_file=test_conf)

    import uvicorn

    uvicorn.run(myapp)
