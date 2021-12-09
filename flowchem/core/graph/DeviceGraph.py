from __future__ import annotations

import inspect
import itertools
from loguru import logger
from pathlib import Path
from types import ModuleType
from typing import Iterable, Dict, Optional, Union, List

import yaml
import networkx as nx

import flowchem.components.devices
from flowchem.core.graph.validation import validate_graph
from flowchem.components.stdlib import Tube, MappedComponentMixin
from flowchem.core.graph.DeviceNode import DeviceNode
from flowchem.exceptions import InvalidConfiguration
from flowchem.units import flowchem_ureg

# Packages containing the device class definitions.
# Devices' classes must be in the module top level to be found.
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

        # NetworkX Multi directed graph object
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()

        # Save config pre-parsing for debug purposes
        self._raw_config = configuration

        # Load graph
        validate_graph(configuration)
        self.parse_graph_file(configuration)

    @classmethod
    def from_file(cls, file: Union[Path, str]):
        """Creates DeviceGraph from config file."""

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

        logger.info(f"Parsed graph {self.name}")

    def _parse_devices(self, devices: Dict):
        """ Parse the devices' section of the graph file """

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
                raise InvalidConfiguration(f"Node config invalid: {node_config}") from e

            # Object type and config
            obj_type = device_mapper[device_class]
            device_config = node_config[device_class]

            # Create device object and add it to the graph
            device = DeviceNode(
                device_name, device_config, obj_type
            ).device
            self.graph.add_node(device)
            logger.debug(f"Added device <{device_name}> as node")

    def _parse_physical_connections(self, connections: Dict):
        """ Parse physical connections from the graph file """
        for edge in connections:
            if "Tube" in edge:
                self._parse_tube_connection(edge["Tube"])
            else:
                raise InvalidConfiguration(f"Invalid connection type in {edge}")

    def _parse_tube_connection(self, tube_config):
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
        self.graph.add_node(tube)
        logger.debug(f"Added tube <{tube.name}> as node")

        # Create logic connections for newly created tube
        inlet = {
            "Interface": {
                "from": dict(device=tube_config["from"]["device"],
                             position=tube_config["from"].get("position", 0)),
                "to": dict(device=tube.name),
            }
        }
        outlet = {
            "Interface": {
                "from": dict(device=tube.name),
                "to": dict(device=tube_config["to"]["device"],
                           position=tube_config["to"].get("position", 0)),
            }
        }
        self._parse_logical_connections([inlet, outlet])

    def _parse_logical_connections(self, connections):
        """ Parse logical connections from the graph file """
        for edge in connections:
            if "Interface" in edge:
                self._parse_interface_connection(edge["Interface"])
            else:
                raise InvalidConfiguration(f"Invalid connection type in {edge}")

    def _parse_interface_connection(self, iface_config):
        """ Parse a dict containing the Tube connection and returns the Connection """
        try:
            from_device = self[iface_config["from"]["device"]]
            to_device = self[iface_config["to"]["device"]]
        except KeyError as ke:
            raise InvalidConfiguration(
                "An Interface refers to a non existing node!\n"
                f"Missing node: {ke}\n"
                f"Interface config: {iface_config}"
            ) from ke

        self.graph.add_edge(from_device, to_device)

        # If necessary updates mapping.
        if iface_config["from"].get("position", 0) != 0:
            position = iface_config["from"]["position"]
            from_device.mapping[position] = to_device.name
        if iface_config["to"].get("position", 0) != 0:
            position = iface_config["to"]["position"]
            to_device.mapping[position] = from_device.name

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
                device for device in self.graph.nodes if isinstance(device, item)
            ]

        # If a string is passed return the device with that name
        elif isinstance(item, str):
            for node in self.graph.nodes:
                if node.name == item:
                    return node
            raise KeyError(f"No component named '{item}' in {repr(self)}.")

        # a shorthand way to check if a component is in the apparatus
        elif item in self.graph.nodes:
            return item
        else:
            raise KeyError(f"{repr(item)} is not in {repr(self)}.")

    def visualize(self):
        """ Visualize the graph """
        import matplotlib.pyplot as plt

        nx.draw(self.graph, with_labels=True)
        plt.show()

    def validate(self) -> bool:
        """ Validates the graph. This is called by Protocol when the DeviceGraph is used."""

        # Make sure that all the components are connected
        if not nx.is_weakly_connected(self.graph):
            logger.warning("Not all components connected.")
            return False

        # Check validity of mappings in mapped components
        for mapped_component in self[MappedComponentMixin]:

            # ensure that component's mapping partners are part of the DeviceGraph
            for component in mapped_component.mapping.values():
                if component is not None and component not in self.graph.nodes:
                    logger.warning(
                        f"Invalid mapping for mapped component {mapped_component}. "
                        f"{component} has not been added to {self.name}!"
                    )
                    return False
        return True

    def summarize(self):
        """
        Prints a summary table of the DeviceGraph.
        Rich takes care of the formatting both in console and jupyter cells.
        """
        from rich.table import Table

        # Components table
        components_table = Table(title=f"Components")

        # Columns: Name, Type
        components_table.add_column("Name")
        components_table.add_column("Type")

        # Fill rows with all devices while skipping tubes (saving them for the second table)
        tubes: List[Tube] = []
        for component in sorted(self.graph.nodes, key=lambda x: x.__class__.__name__):
            if component.__class__.__name__ != "Tube":
                components_table.add_row(component.name, component.__class__.__name__)
            else:
                tubes.append(component)

        # Tubing table
        tubing_table = Table(
            "From", "To", "Length", "I.D.", "O.D.", "Volume", "Material", title="Tubing"
        )

        # store and calculate the computed totals for tubing
        total_length = 0 * flowchem_ureg.mm
        total_volume = 0 * flowchem_ureg.ml

        last_tube = tubes[-1]
        for tube in tubes:
            total_length += tube.length
            total_volume += tube.volume
            from_component = next(self.graph.predecessors(tube))
            to_component = next(self.graph.successors(tube))

            end_section = True if tube is last_tube else False
            print(end_section)

            tubing_table.add_row(
                from_component.name,
                to_component.name,
                f"{tube.length:~H}",
                f"{tube.ID:~H}",
                f"{tube.OD:~H}",
                f"{tube.volume.to('ml'):.4f~H}",
                tube.material,
                end_section=end_section
            )

        tubing_table.add_row(
            "Total",
            "n/a",
            f"{total_length:~H}",
            "n/a",
            "n/a",
            f"{total_volume.to('ml'):.4f~H}",
            "n/a",
        )

        # Print tables
        from rich.console import Console

        console = Console()
        console.print(components_table)
        console.print(tubing_table)


if __name__ == "__main__":
    graph = DeviceGraph.from_file("owen_config2.yml")
    graph.summarize()

    # from flowchem import Protocol
    # a = graph.to_apparatus()
    # print(a)
    # p = Protocol(a)
    #
    # from datetime import timedelta
    # t0 = timedelta(seconds=0)
    #
    # # p.add(graph["quencher"], start=t0, duration=timedelta(seconds=10), rate="0.1 ml/min")
    # p.add(
    #     graph["activator"], start=t0, duration=timedelta(seconds=10), rate="0.1 ml/min"
    # )
    # print(graph["chiller"])
    # print(type(graph["chiller"]))
    # p.add(graph["chiller"], start=t0, duration=timedelta(seconds=10), temp="45 degC")
    #
    # E = p.execute(dry_run=False)
    # # E.visualize()
