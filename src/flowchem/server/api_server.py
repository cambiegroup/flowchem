"""" Run with uvicorn main:app """
import inspect
from pathlib import Path
from typing import Dict

import yaml

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from loguru import logger

import flowchem
from flowchem.models import BaseDevice
from server.config.parser import parse_config_file
from flowchem.exceptions import InvalidConfiguration


def create_server_from_file(config_file: Path) -> FastAPI:
    """
    Based on the yaml device config provided, creates connection to devices and API endpoints.

    config: Path to the yaml file with the device config or dict.
    """
    parsed_config = parse_config_file(config_file)
    return create_server_for_devices(parsed_config["devices"])


def create_server_for_devices(dev_list: list) -> FastAPI:
    """Initialize and create API endpoints for device object provided."""

    # FastAPI server
    app = FastAPI(title="flowchem", version=flowchem.__version__)

    # Parse list of devices and generate endpoints
    for device in dev_list:
        # FIXME do initialization here

        # Get router
        router = device.get_router()

        # Add to App
        app.include_router(router, prefix=router.prefix, tags=router.tags)
        logger.debug(f"Router for <{device.name}> added to app!")

    return app


if __name__ == "__main__":
    myapp = create_server_from_file(config_file=Path("config/sample_config.yml"))

    @myapp.get("/", response_class=HTMLResponse, include_in_schema=False)
    def root():
        """Server root"""
        return "<h1>Flowchem Device Server!</h1>" "<a href='./docs/'>API Reference</a>"

    import uvicorn

    uvicorn.run(myapp, host="127.0.0.1")
