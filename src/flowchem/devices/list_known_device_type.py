"""Auto-discover the device classes present in the device sub-folders and in the installed plugins."""
import inspect
from importlib.metadata import entry_points
from typing import Any

from loguru import logger

import flowchem.devices
from flowchem.models.base_device import BaseDevice


def is_device_class(test_object):
    """Return true if the object is a subclass of BaseDevice."""
    if getattr(test_object, "__module__", None) is None:
        return
    return (
        inspect.isclass(test_object)
        and issubclass(test_object, BaseDevice)
        and test_object.__name__ != "BaseDevice"
    )


def _autodiscover_devices_in_module(module) -> dict[str, Any]:
    """Given a module, autodiscover the device classes and return them as dict(name, object)."""
    device_classes = inspect.getmembers(module, is_device_class)
    # Dict of device class names and their respective classes, i.e. {device_class_name: DeviceClass}.
    return {obj_class[0]: obj_class[1] for obj_class in device_classes}


def autodiscover_first_party() -> dict[str, Any]:
    """Get classes from `flowchem.devices` subpackages."""
    return _autodiscover_devices_in_module(flowchem.devices)


def autodiscover_third_party() -> dict[str, Any]:
    """
    Get classes from packages with a `flowchem.devices` entrypoint.

    A plugin structure can be used to add devices from an external package via setuptools entry points.
    See https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata
    """
    device_classes = {}

    for ep in entry_points(group="flowchem.devices"):
        logger.info(f"Loading third-party module: {ep.name} [from `{ep.module}`]")
        new_device_classes = _autodiscover_devices_in_module(ep.load())
        logger.info(
            f"Found {len(new_device_classes)} device type in {ep.module} {list(new_device_classes.keys())}"
        )
        device_classes.update(new_device_classes)

    return device_classes


def autodiscover_device_classes():
    """Get all the device-controlling classes, either from `flowchem.devices` or third party packages."""
    first_part_objects = autodiscover_first_party()
    logger.info(f"{len(first_part_objects)} first-party device type found!")
    third_part_objects = autodiscover_third_party()
    logger.info(f"{len(third_part_objects)} third-party device type found!")

    # For duplicate the first party will overwrite the third party ones. Ensure unique names! ;)
    return third_part_objects | first_part_objects


if __name__ == "__main__":
    logger.info(
        f"The following device types were found: {list(autodiscover_device_classes().keys())}"
    )
