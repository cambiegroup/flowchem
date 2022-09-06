""" Parse a device config file. """
from __future__ import annotations

import inspect
import itertools
from pathlib import Path
from typing import Dict

# For Python >= 3.11 use stdlib tomllib instead of tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import flowchem
from flowchem.exceptions import InvalidConfiguration
from flowchem.models import BaseDevice
from loguru import logger

# Packages containing the device class definitions.
DEVICE_MODULES = [flowchem.devices]

# Devices' classes must be in the module top level to be found.
_objects_in_modules = [
    inspect.getmembers(module, inspect.isclass) for module in DEVICE_MODULES
]

# Dict of device class names and their respective classes, i.e. {device_class_name: DeviceClass}.
DEVICE_MAPPER = dict(itertools.chain.from_iterable(_objects_in_modules))


def parse_config_file(file_path: Path) -> Dict:
    """Parse a config file."""

    with file_path.open('rb') as stream:
        try:
            config = tomllib.load(stream)
        except tomllib.TOMLDecodeError as parser_error:
            logger.exception(parser_error)
            raise InvalidConfiguration(
                f"The configuration file {file_path} is not a valid TOML file!"
            ) from parser_error

    config["filename"] = file_path.stem
    return parse_config(config)


def parse_config(graph_config: Dict) -> Dict:
    """Parse config."""

    # Parse devices
    graph_config["devices"] = [parse_device(dev) for dev in graph_config["devices"]]
    logger.info("Parsed config!")

    return graph_config


def parse_device(device_dict) -> BaseDevice:
    """Parse device config and return a device object."""
    device_class, device_config = next(iter(device_dict.items()))

    if device_config is None:
        device_config = {}

    try:
        obj_type = DEVICE_MAPPER[device_class]
    except KeyError as error:
        logger.exception(
            f"Device of type {device_class} unknown! [Known devices: {DEVICE_MAPPER.keys()}]"
        )
        raise InvalidConfiguration(
            f"Device of type {device_class} unknown! \n"
            f"[Known devices: {list(DEVICE_MAPPER.keys())}]"
        ) from error

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
