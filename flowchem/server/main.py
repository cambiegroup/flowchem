"""" Run with uvicorn main:app """
import json
from pathlib import Path

import os

import jsonschema
import yaml
import logging
import flowchem
import inspect
import itertools
from types import ModuleType
from typing import Iterable, Dict, Tuple, Union

from fastapi import FastAPI
from mdns_server import Server_mDNS
from device_node_creator import DeviceNode
from flowchem.server import test_devices

logger = logging.getLogger(__name__)

# packages containing the device class definitions. Target classes should be available in the module top level.
DEVICE_MODULES = [flowchem, test_devices]
SCHEMA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "flowchem-graph-spec.schema"
)


def get_device_class_mapper(modules: Iterable[ModuleType]) -> Dict[str, type]:
    """
    Given an iterable of modules containing the device classes, return a
    dictionary Dict[device_class_name, DeviceClass]

    Args:
        modules (Iterable[ModuleType]): The modules to inspect for devices.
            Only class in the top level of each module will be extracted.
    Returns:
        device_dict (Dict[str, type]): Dict of device class names and their
            respective classes, i.e. {device_class_name: DeviceClass}.
    """
    # Get (name, obj) tuple for the top level of each modules.
    objects_in_modules = [
        inspect.getmembers(module, inspect.isclass) for module in modules
    ]

    # Return them as dict (itertools to flatten the nested, per module, lists)
    return {k: v for (k, v) in itertools.chain.from_iterable(objects_in_modules)}


def load_schema():
    """ loads the schema defining valid config file. """
    with open(SCHEMA, "r") as fp:
        schema = json.load(fp)
        jsonschema.Draft7Validator.check_schema(schema)
        return schema


def create_server_from_config(config: Union[Path, Dict]) -> Tuple[FastAPI, Server_mDNS]:
    """
    Based on the yaml device graph provided, creates device objects and connect to them + .

    config: Path to the yaml file with the device config or dict.
    """
    if isinstance(config, Path):
        with config.open() as stream:
            config = yaml.safe_load(stream)

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

    app, zeroconf = create_server_from_config(Path("sample_config.yml"))

    @app.get("/")
    def root():
        """ Server root """
        # FIXME add landing page
        return "<h1>hello world!</h1>"

    import uvicorn

    uvi = uvicorn.run(app, host="0.0.0.0")
