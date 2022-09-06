""" Parse a device config file. """
import inspect
import itertools
from pathlib import Path
from typing import Dict

# For Python >= 3.11 use stdlib tomllib instead of tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import flowchem.devices
from flowchem.exceptions import InvalidConfiguration
from flowchem.models.base_device import BaseDevice
from loguru import logger

# Device classes must be in the flowchem.devices. Use plugin structure to add from external packages.
_objects_in_modules = inspect.getmembers(flowchem.devices, inspect.isclass)

# Dict of device class names and their respective classes, i.e. {device_class_name: DeviceClass}.
DEVICE_MAPPER = {obj_class[0]: obj_class[1] for obj_class in _objects_in_modules}


def load_configuration_file(file_path: Path) -> Dict:
    """Read the TOML configuration file and returns it as a dict.

    Extensive exception handling due to the error-prone human editing needed in the configuration file."""
    with file_path.open("rb") as stream:
        try:
            return tomllib.load(stream)
        except tomllib.TOMLDecodeError as parser_error:
            logger.exception(parser_error)
            raise InvalidConfiguration(
                f"The configuration file {file_path} is not a valid TOML file!"
            ) from parser_error


def parse_config_file(file_path: Path | str) -> Dict:
    """Parse a config file."""

    file_path = Path(file_path)
    config = load_configuration_file(file_path)
    config["filename"] = file_path.stem
    return parse_config(config)


def parse_config(config: Dict) -> Dict:
    """Parse config."""

    # Iterate on all devices, parse device-specific settings and instantiate the relevant objects
    config["device"] = [
        parse_device(dev_settings) for dev_settings in config["device"].items()
    ]
    logger.info("Configuration parsed!")

    return config


def parse_device(dev_settings) -> BaseDevice:
    """Parse device config and return a device object.

    Exception handling to provide more specific and diagnostic messages upon errors in the configuration file."""
    device_name, device_config = dev_settings

    # Get device class
    try:
        obj_type = DEVICE_MAPPER[device_config["type"]]
        del device_config["type"]
    except KeyError as error:
        logger.exception(
            f"Device type unknown for '{device_name}'! [Known device types are: {DEVICE_MAPPER.keys()}]"
        )
        raise InvalidConfiguration(
            f"Device type unknown for {device_name}! \n"
        ) from error

    # Instantiate it with the provided settings
    if hasattr(obj_type, "from_config"):
        try:
            device = obj_type.from_config(**device_config)
            logger.debug(f"Created device '{device.name}' instance: {device}")
        except TypeError as error:
            raise ConnectionError(
                f"Wrong configuration provided for device: {device_name} of type {obj_type.__name__}!\n"
                f"Configuration: {device_config}\n"
                f"Accepted parameters: {inspect.getfullargspec(obj_type.from_config).args}"
            ) from error
    else:

        try:
            device = obj_type(**device_config)
            logger.debug(f"Created device '{device.name}' instance: {device}")
        except TypeError as error:
            raise ConnectionError(
                f"Wrong configuration provided for device: {device_name} of type {obj_type.__name__}!\n"
                f"Configuration: {device_config}\n"
                f"Accepted parameters: {inspect.getfullargspec(obj_type).args}"
            ) from error
        return device


if __name__ == "__main__":
    cfg = parse_config_file("sample_configuration.toml")
    print(cfg)
