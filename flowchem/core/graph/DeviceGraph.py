from __future__ import annotations

import inspect
import itertools
import json
import os
from loguru import logger
from collections import namedtuple
from pathlib import Path
from types import ModuleType
from typing import Iterable, Dict, Optional, Any, List, Union

import jsonschema
import yaml

import flowchem.components.devices
from flowchem.components.stdlib import Tube, Interface
from flowchem.core.apparatus import Apparatus
from flowchem.core.graph.DeviceNode import DeviceNode
from flowchem.exceptions import InvalidConfiguration

# packages containing the device class definitions. Target classes should be available in the module top level.
DEVICE_MODULES = [flowchem.components.devices, flowchem.components.stdlib, flowchem.components.reactors]

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
    """loads the schema defining valid config file."""
    with open(SCHEMA, "r") as fp:
        schema = json.load(fp)
        jsonschema.Draft7Validator.check_schema(schema)
        return schema


Connection = namedtuple("Connection", ["from_device", "to_device", "tube"])


class DeviceGraph:
    """
    Represents the device graph.

    This borrows logic from mw.Apparatus and ChempilerGraph
    """

    _id_counter = 0

    def __init__(self, configuration, name: Optional[str] = None):
        # if given a name, then name the apparatus, else default to a sequential name
        if name is not None:
            self.name = name
        else:
            self.name = "DeviceGraph" + str(DeviceGraph._id_counter)
            DeviceGraph._id_counter += 1

        # dict of devices with names as keys
        self.device: Dict[str, Any] = {}
        # Edge list represents the network topology
        self.edge_list: List[Connection] = []

        # Save config pre-parsing for debug purposes
        self._raw_config = configuration

        # Load graph
        # self.validate(configuration)
        self.parse(configuration)

    @classmethod
    def from_file(cls, file: Union[Path, str]):
        """Creates DeviceGraph from config file"""

        file_path = Path(file)
        name = file_path.stem

        with file_path.open() as stream:
            config = yaml.safe_load(stream)

        return cls(config, name)

    def validate(self, config):
        """Validates config syntax."""
        schema = load_schema()
        jsonschema.validate(config, schema=schema)

    def parse(self, config: Dict):
        """Parse config and generate graph."""

        # Device mapper
        device_mapper = get_device_class_mapper(DEVICE_MODULES)
        logger.debug(
            f"The following device classes have been found: {device_mapper.keys()}"
        )

        # Parse list of devices and create nodes
        for device_name, node_config in config["devices"].items():
            # Schema validation should ensure 1 hit here
            try:
                device_class = [
                    name for name in device_mapper.keys() if name in node_config
                ].pop()
            except IndexError as e:
                raise InvalidConfiguration(f"Node config invalid: {node_config}") from e

            # Object type
            obj_type = device_mapper[device_class]
            device_config = node_config[device_class]

            self.device[device_name] = DeviceNode(
                device_name, device_config, obj_type
            ).device
            logger.debug(
                f"Created device <{device_name}> with config: {device_config}"
            )

        # Parse list of connections
        connections = self._parse_connections(config["connections"])
        self.edge_list.extend(connections)

    def _parse_connections(self, connections: Dict) -> List[Connection]:
        """ Parse connections from config. """
        connection_list = []
        for edge in connections:
            if "Tube" in edge:
                connection = self.parse_tube_connection(edge["Tube"])
            elif "Interface" in edge:
                connection = self.parse_interface_connection(edge["Interface"])
            else:
                raise InvalidConfiguration(f"Invalid connection type in {edge}")

            connection_list.append(connection)

        return connection_list

    def parse_tube_connection(self, tube_config) -> Connection:
        """ Parse a dict containing the Tube connection and returns the Connection """
        tube = Tube(
            length=tube_config["length"],
            ID=tube_config["inner-diameter"],
            OD=tube_config["outer-diameter"],
            material=tube_config["material"],
        )

        # Devices
        try:
            from_device = self.device[tube_config["from"]["device"]]
            to_device = self.device[tube_config["to"]["device"]]
        except KeyError as ke:
            raise InvalidConfiguration("A Tube refers to a non existing node!\n"
                                       f"Missing node: {ke}\n"
                                       f"Tube config: {tube_config}") from ke

        # If necessary updates mapping.
        if tube_config["from"].get("position", 0) != 0:
            position = tube_config["from"]["position"]
            from_device.mapping[position] = from_device.name
        if tube_config["to"].get("position", 0) != 0:
            position = tube_config["to"]["position"]
            to_device.mapping[position] = to_device.name

        return Connection(from_device, to_device, tube)

    def parse_interface_connection(self, iface_config) -> Connection:
        """ Parse a dict containing the Tube connection and returns the Connection """
        interface = Interface()

        try:
            from_device = self.device[iface_config["from"]["device"]]
            to_device = self.device[iface_config["to"]["device"]]
        except KeyError as ke:
            raise InvalidConfiguration("An Interface refers to a non existing node!\n"
                                       f"Missing node: {ke}\n"
                                       f"Interface config: {iface_config}") from ke

        return Connection(from_device, to_device, interface)

    def to_apparatus(self) -> Apparatus:
        """
        Convert the graph to an mw.Apparatus object.
        """

        appa = Apparatus(
            self.name, "Apparatus auto-generated from flowchem DeviceGraph."
        )
        for edge in self.edge_list:
            print(edge)
            print(edge.from_device)
            print(edge.to_device)
            print(edge.tube)

            appa.add(edge.from_device, edge.to_device, edge.tube)
        return appa

    def __repr__(self):
        return f"<DeviceGraph {self.name}>"

    def __str__(self):
        return f"DeviceGraph {self.name} with {len(self.device)} devices."

    def __getitem__(self, item):
        """
        Utility method

        DeviceGraph['name'] gives the device with that name
        DeviceGraph[class] returns a list of devices of that type
        DeviceGraph[device_instance] returns true if the object is part of the graph
        """

        # If a type is passed return devices with that type
        if isinstance(item, type):
            return [
                device for device in self.device.values() if isinstance(device, item)
            ]
        # If a string is passed return the device with that name
        elif isinstance(item, str):
            try:
                return self.device[item]
            except IndexError:
                raise KeyError(f"No component named '{item}' in {repr(self)}.")

        # a shorthand way to check if a component is in the apparatus
        elif item in self.device.values():
            return item
        else:
            raise KeyError(f"{repr(item)} is not in {repr(self)}.")


if __name__ == "__main__":
    from flowchem import Protocol
    from datetime import timedelta

    graph = DeviceGraph.from_file("owen_config.yml")

    a = graph.to_apparatus()
    print(a)
    p = Protocol(a)

    t0 = timedelta(seconds=0)

    # p.add(graph["quencher"], start=t0, duration=timedelta(seconds=10), rate="0.1 ml/min")
    p.add(graph["activator"], start=t0, duration=timedelta(seconds=10), rate="0.1 ml/min")
    print(graph["chiller"])
    print(type(graph["chiller"]))
    p.add(graph["chiller"], start=t0, duration=timedelta(seconds=10), temp="45 degC")

    E = p.execute(dry_run=False)
    # E.visualize()
