from __future__ import annotations

import inspect
import itertools
from loguru import logger
from collections import namedtuple
from pathlib import Path
from types import ModuleType
from typing import Iterable, Dict, Optional, Any, List, Union

import jsonschema
import yaml

import flowchem.components.devices
from core.graph.validation import load_graph_schema, validate_graph
from flowchem.components.stdlib import Tube, Interface
from flowchem.core.apparatus import Apparatus
from flowchem.core.graph.DeviceNode import DeviceNode
from flowchem.exceptions import InvalidConfiguration

# packages containing the device class definitions. Target classes should be available in the module top level.
DEVICE_MODULES = [
    flowchem.components.devices,
    flowchem.components.stdlib,
    flowchem.components.reactors,
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
    # Get (name, obj) tuple for the top level of each modules.
    objects_in_modules = [
        inspect.getmembers(module, inspect.isclass) for module in modules
    ]

    # Return them as dict (itertools to flatten the nested, per module, lists)
    return {k: v for (k, v) in itertools.chain.from_iterable(objects_in_modules)}


Connection = namedtuple("Connection", ["from_device", "to_device", "tube"])


class DeviceGraph:
    """
    Represents the device graph.

    This borrows logic from mw.Apparatus and ChempilerGraph
    """

    _id_counter = 0

    def __init__(self, configuration: Dict, name: Optional[str] = None):
        # if given a name, then name the apparatus, else default to a sequential name
        if name is not None:
            self.name = name
        else:
            self.name = "DeviceGraph" + str(DeviceGraph._id_counter)
            DeviceGraph._id_counter += 1

        # dict of components with names as keys
        self.components: Dict[str, Any] = {}
        # Edge list represents the network topology
        self.edge_list: List[Connection] = []

        # Save config pre-parsing for debug purposes
        self._raw_config = configuration

        # Load graph
        validate_graph(configuration)
        self.parse_graph_file(configuration)

    @classmethod
    def from_file(cls, file: Union[Path, str]):
        """Creates DeviceGraph from config file"""

        file_path = Path(file)
        name = file_path.stem

        with file_path.open() as stream:
            config = yaml.safe_load(stream)

        return cls(config, name)

    def parse_graph_file(self, config: Dict):
        """Parse config and generate graph."""

        # Parse devices
        self._parse_devices(config["devices"])

        # Parse physical connections
        self._parse_physical_connections(config["physical_connections"])

        # Parse logical connections
        if "logical_connections" in config:
            self._parse_logical_connections(config["logical_connections"])

    def _parse_devices(self, devices: Dict):
        """ Parse the devices' section of the graph file """

        # Device mapper needed for device instantiation
        device_mapper = get_device_class_mapper(DEVICE_MODULES)
        logger.debug(
            f"The following device classes have been found: {device_mapper.keys()}"
        )

        # Parse devices
        for device_name, node_config in devices.items():
            # Schema validation ensures 1 hit here
            try:
                device_class = [
                    name for name in device_mapper.keys() if name in node_config
                ].pop()
            except IndexError as e:
                raise InvalidConfiguration(f"Node config invalid: {node_config}") from e

            # Object type
            obj_type = device_mapper[device_class]
            device_config = node_config[device_class]

            self.components[device_name] = DeviceNode(
                device_name, device_config, obj_type
            ).device
            logger.debug(f"Created device <{device_name}> with config: {device_config}")

    def _parse_logical_connections(self, param):
        """ Parse logical connections from the graph file """
        pass

    def _parse_physical_connections(self, connections: Dict):
        """ Parse physical connections from the graph file """
        for edge in connections:
            if "Tube" in edge:
                connection = self._parse_tube_connection(edge["Tube"])
            else:
                raise InvalidConfiguration(f"Invalid connection type in {edge}")

            self.edge_list.append(connection)

    def _parse_tube_connection(self, tube_config) -> Connection:
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

        # Devices
        try:
            from_device = self.components[tube_config["from"]["device"]]
            to_device = self.components[tube_config["to"]["device"]]
        except KeyError as ke:
            raise InvalidConfiguration(
                "A Tube refers to a non existing node!\n"
                f"Missing node: {ke}\n"
                f"Tube config: {tube_config}"
            ) from ke

        # If necessary updates mapping.
        if tube_config["from"].get("position", 0) != 0:
            position = tube_config["from"]["position"]
            from_device.mapping[position] = from_device.name
        if tube_config["to"].get("position", 0) != 0:
            position = tube_config["to"]["position"]
            to_device.mapping[position] = to_device.name

        return Connection(from_device, to_device, tube)

    def _parse_interface_connection(self, iface_config) -> Connection:
        """ Parse a dict containing the Tube connection and returns the Connection """
        interface = Interface()

        try:
            from_device = self.components[iface_config["from"]["device"]]
            to_device = self.components[iface_config["to"]["device"]]
        except KeyError as ke:
            raise InvalidConfiguration(
                "An Interface refers to a non existing node!\n"
                f"Missing node: {ke}\n"
                f"Interface config: {iface_config}"
            ) from ke

        return Connection(from_device, to_device, interface)

    def to_apparatus(self) -> Apparatus:
        """
        Convert the graph to Apparatus object.
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
        return f"DeviceGraph {self.name} with {len(self.components)} devices."

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
                device for device in self.components.values() if isinstance(device, item)
            ]

        # If a string is passed return the device with that name
        elif isinstance(item, str):
            try:
                return self.components[item]
            except IndexError:
                raise KeyError(f"No component named '{item}' in {repr(self)}.")

        # a shorthand way to check if a component is in the apparatus
        elif item in self.components.values():
            return item
        else:
            raise KeyError(f"{repr(item)} is not in {repr(self)}.")


if __name__ == "__main__":
    from flowchem import Protocol
    from datetime import timedelta

    graph = DeviceGraph.from_file("owen_config2.yml")

    a = graph.to_apparatus()
    print(a)
    p = Protocol(a)

    t0 = timedelta(seconds=0)

    # p.add(graph["quencher"], start=t0, duration=timedelta(seconds=10), rate="0.1 ml/min")
    p.add(
        graph["activator"], start=t0, duration=timedelta(seconds=10), rate="0.1 ml/min"
    )
    print(graph["chiller"])
    print(type(graph["chiller"]))
    p.add(graph["chiller"], start=t0, duration=timedelta(seconds=10), temp="45 degC")

    E = p.execute(dry_run=False)
    # E.visualize()
