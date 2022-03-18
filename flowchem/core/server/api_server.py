"""" Run with uvicorn main:app """
from pathlib import Path
from typing import Dict

import yaml
from flowchem.core.graph.validation import validate_graph
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from loguru import logger

import flowchem
from flowchem.core.graph.devicenode import DeviceNode
from flowchem.core.graph.parser import DEVICE_MODULES, get_device_class_mapper
from flowchem.exceptions import InvalidConfiguration


def create_server_from_config(config: Dict = None, config_file: Path = None) -> FastAPI:
    """
    Based on the yaml device graph provided, creates device objects and connect to them + .

    config: Path to the yaml file with the device config or dict.
    """

    assert (
        config is not None
        and config_file is None
        or config is None
        and config_file is not None
    )

    if config_file is not None:
        with config_file.open() as stream:
            config = yaml.safe_load(stream)

    assert isinstance(config, dict)  # This is here just to make mypy happy.

    # Validate config
    validate_graph(config)

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

        node = DeviceNode(device_config, obj_type)
        logger.debug(f"Created device <{device_name}> with config: {device_config}")

        # Add to App
        app.include_router(
            node.router, prefix=node.router.prefix, tags=node.router.tags
        )
        logger.debug(f"Router for <{device_name}> added to app!")

    return app


if __name__ == "__main__":
    myapp = create_server_from_config(config_file=Path("../graph/sample_config.yml"))

    @myapp.get("/", response_class=HTMLResponse, include_in_schema=False)
    def root():
        """Server root"""
        return "<h1>Flowchem Device Server!</h1>" "<a href='./docs/'>API Reference</a>"

    import uvicorn

    uvicorn.run(myapp, host="127.0.0.1")
