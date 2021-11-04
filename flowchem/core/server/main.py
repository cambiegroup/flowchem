"""" Run with uvicorn main:app """
import logging
from pathlib import Path
from typing import Dict, Tuple

import jsonschema
import yaml
from fastapi import FastAPI

import flowchem
from flowchem.graph.DeviceGraph import (
    DEVICE_MODULES,
    get_device_class_mapper,
    load_schema,
)
from flowchem.graph.DeviceNode import DeviceNode
from mdns_server import Server_mDNS

logger = logging.getLogger(__name__)


def create_server_from_config(
    config: Dict = None, config_file: Path = None
) -> Tuple[FastAPI, Server_mDNS]:
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
    schema = load_schema()
    jsonschema.validate(config, schema=schema)

    # FastAPI server
    app = FastAPI(title="flowchem", version=flowchem.__version__)

    # Zeroconf server
    zeroconf = Server_mDNS()

    # Device mapper
    device_mapper = get_device_class_mapper(DEVICE_MODULES)
    logger.debug(
        f"The following device classes have been found: {device_mapper.keys()}"
    )

    # Parse list of devices and generate endpoints
    for device_name, node_config in config["devices"].items():
        # Schema validation ensures only 1 hit here
        device_class = [
            name for name in device_mapper.keys() if name in node_config
        ].pop()

        # Object type
        obj_type = device_mapper[device_class]
        device_config = node_config[device_class]

        node = DeviceNode(device_name, device_config, obj_type)
        logger.debug(f"Created device <{device_name}> with config: {device_config}")

        # Add to App
        app.include_router(node.router, prefix=node.router.prefix)
        logger.debug(f"Router for <{device_name}> added to app!")

        # Add to mDNS server
        zeroconf.include_device(node.safe_title, node.router.prefix)
        logger.debug(f"Router for <{device_name}> added to app!")

    return app, zeroconf


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    app, zeroconf = create_server_from_config(
        config_file=Path("../graph/sample_config.yml")
    )

    @app.get("/")
    def root():
        """Server root"""
        # FIXME add landing page
        return "<h1>hello world!</h1>"

    import uvicorn

    uvi = uvicorn.run(app, host="0.0.0.0")
