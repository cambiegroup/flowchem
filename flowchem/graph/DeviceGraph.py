from __future__ import annotations

import inspect
import itertools
import json
import logging
import os
from pathlib import Path
from types import ModuleType
from typing import *

import jsonschema
import yaml

import flowchem
from server import test_devices

# packages containing the device class definitions. Target classes should be available in the module top level.
DEVICE_MODULES = [flowchem, test_devices]

# Validation schema for graph file
SCHEMA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "../graph/flowchem-graph-spec.schema"
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


class DeviceGraph:
    """
    Represents the device graph.

    This borrows logic from mw.Apparatus and ChempilerGraph
    """
    def __init__(self, configuration):

        # Save config pre-parsing for debug purposes
        self._raw_config = configuration

        # Logger
        self.log = logging.getLogger(__name__).getChild("DeviceGraph")

        # Load graph
        # self.validate(configuration)
        self.parse(configuration)

    @classmethod
    def from_file(cls, file: Union[Path, str]):
        """ Creates DeviceGraph from config file """

        file_path = Path(file)

        with file_path.open() as stream:
            config = yaml.safe_load(stream)

        return cls(config)

    def validate(self, config):
        """ Validates config syntax. """
        schema = load_schema()
        jsonschema.validate(config, schema=schema)

    def parse(self, configuration: Dict):
        """ Parse config and generate graph. """

        # Device mapper
        device_mapper = get_device_class_mapper(DEVICE_MODULES)
        self.log.debug(
            f"The following device classes have been found: {device_mapper.keys()}"
        )






