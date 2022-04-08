"""" Run with uvicorn main:app """
import inspect
from pathlib import Path
from typing import Dict

import yaml
from server.config.validator import validate_config
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from loguru import logger

import flowchem
from flowchem.models import BaseDevice
from server.config.parser import DEVICE_MODULES, get_device_class_mapper
from flowchem.exceptions import InvalidConfiguration


def parse_device_config(obj_type, device_config=None) -> BaseDevice:
    """ Parse device config and return a device object. """
    if device_config is None:
        device_config = {}

        # DEVICE INSTANTIATION
    try:
        device = obj_type(**device_config)
        logger.debug(f"Created device '{device.name}' instance: {device}")
    except TypeError as error:
        raise ConnectionError(
            f"Wrong configuration provided for device: {device_config.get('name')} of type {obj_type}!\n"
            f"Configuration: {device_config}\n"
            f"Accepted parameters: {inspect.getfullargspec(obj_type).args}"
        ) from error
    return device


def create_server_from_file(config_file: Path) -> FastAPI:
    """
    Based on the yaml device config provided, creates connection to devices and API endpoints.

    config: Path to the yaml file with the device config or dict.
    """
    if config_file is not None:
        with config_file.open() as stream:
            config = yaml.safe_load(stream)
    return create_server_from_config(config)


def create_server_from_config(config: Dict = None) -> FastAPI:
    """
    Based on the yaml device config provided, creates connection to devices and API endpoints.

    config: dict.
    """

    # Validate config
    validate_config(config)

    # FastAPI server
    app = FastAPI(title="flowchem", version=flowchem.__version__)

    # Device mapper
    device_mapper = get_device_class_mapper(DEVICE_MODULES)
    logger.debug(
        f"The following device classes have been found: {device_mapper.keys()}"
    )

    # Parse list of devices and generate endpoints
    for device_name, node_config in config["devices"].items():
        # Schema validation ensures only 1 hit here
        try:
            device_class = [
                name for name in device_mapper.keys() if name in node_config
            ].pop()
        except IndexError as error:
            raise InvalidConfiguration(
                f"No class available for device '{device_name}'"
            ) from error

        # Object type
        obj_type = device_mapper[device_class]
        device_config = node_config[device_class]
        device = parse_device_config(obj_type, device_config)
        router = device.get_router()

        # Add to App
        app.include_router(router, prefix=router.prefix, tags=router.tags)
        logger.debug(f"Router for <{device_name}> added to app!")

    return app


if __name__ == "__main__":
    myapp = create_server_from_file(config_file=Path("config/sample_config.yml"))

    @myapp.get("/", response_class=HTMLResponse, include_in_schema=False)
    def root():
        """Server root"""
        return "<h1>Flowchem Device Server!</h1>" "<a href='./docs/'>API Reference</a>"

    import uvicorn

    uvicorn.run(myapp, host="127.0.0.1")
