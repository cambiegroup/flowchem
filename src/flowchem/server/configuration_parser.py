""" Parse a device config file. """
import inspect
import sys
from pathlib import Path

from flowchem.devices.find_device_type import autodiscover_device_classes


if sys.version_info >= (3, 11):
    # noinspection PyUnresolvedReferences
    import tomllib
else:
    import tomli as tomllib

from flowchem.exceptions import InvalidConfiguration
from flowchem.models.base_device import BaseDevice
from loguru import logger


def load_configuration_file(file_path: Path) -> dict:
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


def parse_config_file(file_path: Path | str) -> dict:
    """Parse a config file."""

    file_path = Path(file_path)
    assert file_path.exists() and file_path.is_file(), f"Does the provided configuration file {file_path} exist?"
    config = load_configuration_file(file_path)
    config["filename"] = file_path.stem
    return parse_config(config)


def parse_config(config: dict) -> dict:
    """Parse config."""
    # This creates a dict with device type as key and object to be instantiated as values.
    device_mapper = autodiscover_device_classes()

    # Iterate on all devices, parse device-specific settings and instantiate the relevant objects
    config["device"] = [
        parse_device(dev_settings, device_mapper)
        for dev_settings in config["device"].items()
    ]
    logger.info("Configuration parsed!")

    return config


def parse_device(dev_settings, device_object_mapper) -> BaseDevice:
    """Parse device config and return a device object.

    Exception handling to provide more specific and diagnostic messages upon errors in the configuration file."""
    device_name, device_config = dev_settings

    # Get device class
    try:
        obj_type = device_object_mapper[device_config["type"]]
        del device_config["type"]
    except KeyError as error:
        logger.exception(
            f"Device type unknown for '{device_name}'! [Known device types are: {device_object_mapper.keys()}]"
        )
        raise InvalidConfiguration(
            f"Device type unknown for {device_name}! \n"
        ) from error

    # If the object has a 'from_config' method, use that for instantiation, otherwise try straight with the constructor.
    try:
        if hasattr(obj_type, "from_config"):
            called = obj_type.from_config
            device = obj_type.from_config(**device_config, name=device_name)
        else:
            called = obj_type.__init__
            device = obj_type(**device_config, name=device_name)
    except TypeError as error:
        logger.error(f"Wrong settings for device '{device_name}'!")
        get_helpful_error_message(device_config, inspect.getfullargspec(called))
        raise ConnectionError(
            f"Wrong configuration provided for device '{device_name}' of type {obj_type.__name__}!\n"
            f"Configuration: {device_config}\n"
            f"Accepted parameters: {inspect.getfullargspec(called).args}"
        ) from error

    logger.debug(f"Created device '{device.name}' instance: {device}")
    return device


def get_helpful_error_message(called_with: dict, arg_spec: inspect.FullArgSpec):
    """Give helpful debugging text on configuration errors."""
    # First check if we have provided an argument that is not supported.
    if (
        arg_spec.varkw is None
    ):  # Clearly no **kwargs should be defined in the signature otherwise all kwargs are ok
        invalid_parameters = list(set(called_with.keys()).difference(arg_spec.args))
        if invalid_parameters:
            logger.error(
                f"The following parameters were not recognized: {invalid_parameters}"
            )

    # Then check if a mandatory arguments was not satisfied. [1 to skip cls/self, -n to remove args w/ default]
    mandatory_args = arg_spec.args[1 : -len(arg_spec.defaults)]  # type: ignore
    missing_parameters = list(set(mandatory_args).difference(called_with.keys()))
    if missing_parameters:
        logger.error(
            f"The following mandatory parameters were missing in the configuration: {missing_parameters}"
        )


if __name__ == "__main__":
    cfg = parse_config_file("sample_configuration.toml")
    print(cfg)
