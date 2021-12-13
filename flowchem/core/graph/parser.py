import yaml
from pathlib import Path
from typing import Union, Dict, Iterable
from loguru import logger
from types import ModuleType
import inspect
import itertools

from flowchem.components.stdlib import Tube
from flowchem.core.graph.devicenode import DeviceNode
from flowchem.core.graph.validation import validate_graph
from flowchem.exceptions import InvalidConfiguration
from flowchem.core.graph.devicegraph import DeviceGraph
import flowchem.assemblies


# Packages containing the device class definitions.
# Devices' classes must be in the module top level to be found.
DEVICE_MODULES = [
    flowchem.components.devices,
    flowchem.components.stdlib,
    flowchem.components.dummy,
    flowchem.assemblies,
]


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
    # Get (name, obj) tuple for the top level of each module.
    objects_in_modules = [
        inspect.getmembers(module, inspect.isclass) for module in modules
    ]

    # Return them as dict (itertools to flatten the nested, per module, lists)
    return {k: v for (k, v) in itertools.chain.from_iterable(objects_in_modules)}


def parse_device_section(devices: Dict, graph: DeviceGraph):
    """Parse the devices' section of the graph config"""

    # Device mapper needed for device instantiation
    device_mapper = get_device_class_mapper(DEVICE_MODULES)
    logger.debug(f"Device classes found: {device_mapper.keys()}")

    # Parse devices
    for device_name, node_config in devices.items():
        # Schema validation ensures 1 hit here
        try:
            device_class = [
                name for name in device_mapper.keys() if name in node_config
            ].pop()
        except IndexError as e:
            logger.exception(f"Invalid device configuration: {node_config}")
            raise InvalidConfiguration(
                f"Invalid device configuration: {node_config}"
            ) from e

        # Object type and config
        obj_type = device_mapper[device_class]
        device_config = node_config[device_class]

        # Create device object and add it to the graph
        device = DeviceNode(device_name, device_config, obj_type).device
        graph.add_device(device)


def parse_physical_connections(connections: Dict, graph: DeviceGraph):
    """Parse physical connections from the graph config"""
    for edge in connections:
        if "Tube" in edge:
            _parse_tube_connection(edge["Tube"], graph)
        else:
            raise InvalidConfiguration(f"Invalid connection type in {edge}")


def _parse_tube_connection(tube_config, graph: DeviceGraph):
    """
    The Tube object is a convenience object for connecting devices without explicitly creating the
    in-between tube node.
    """
    tube = Tube(
        length=tube_config["length"],
        ID=tube_config["inner-diameter"],
        OD=tube_config["outer-diameter"],
        material=tube_config["material"],
    )
    graph.add_device(tube)

    # Create logic connections for newly created tube
    inlet = {
        "Interface": {
            "from": dict(
                device=tube_config["from"]["device"],
                position=tube_config["from"].get("position", 0),
            ),
            "to": dict(device=tube.name),
        }
    }
    outlet = {
        "Interface": {
            "from": dict(device=tube.name),
            "to": dict(
                device=tube_config["to"]["device"],
                position=tube_config["to"].get("position", 0),
            ),
        }
    }
    parse_logical_connections([inlet, outlet], graph)


def parse_logical_connections(connections, graph: DeviceGraph):
    """Parse logical connections from the graph config"""
    for edge in connections:
        if "Interface" in edge:
            _parse_interface_connection(edge["Interface"], graph)
        else:
            raise InvalidConfiguration(f"Invalid connection type in {edge}")


def _parse_interface_connection(iface_config, graph: DeviceGraph):
    """Parse a dict containing the Tube connection and returns the Connection"""
    graph.add_connection(
        origin=iface_config["from"]["device"],
        destination=iface_config["to"]["device"],
        origin_port=iface_config["from"].get("position", None),
        destination_port=iface_config["to"].get("position", None),
    )


def parse_graph_config(graph_config: Dict, name: str = None) -> DeviceGraph:
    """Parse a graph config and returns a DeviceGraph object."""

    # Validate graph
    validate_graph(graph_config)

    # Create DeviceGraph object
    device_graph = DeviceGraph(name)

    # Parse devices
    parse_device_section(graph_config["devices"], device_graph)

    # Parse physical connections
    parse_physical_connections(graph_config["physical_connections"], device_graph)

    # Parse logical connections
    if "logical_connections" in graph_config:
        parse_logical_connections(graph_config["logical_connections"], device_graph)

    logger.info(f"Parsed graph {name}")
    return device_graph


def parse_graph_file(file: Union[str, Path]):
    """Parse a graph config file and returns a DeviceGraph object."""
    file_path = Path(file)
    name = file_path.stem

    with file_path.open() as stream:
        config = yaml.safe_load(stream)

    return parse_graph_config(config, name)
