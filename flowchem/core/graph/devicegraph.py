from __future__ import annotations

from loguru import logger
from typing import Optional, Union, List, Iterable, Any

import networkx as nx

from flowchem.exceptions import InvalidConfiguration
from flowchem.components.properties import Component, MultiportComponentMixin
from flowchem.components.stdlib import Tube
from flowchem.assemblies import Assembly
from flowchem.units import flowchem_ureg


class DeviceGraph:
    """
    Represents the device graph.

    This borrows logic from mw.Apparatus and ChempilerGraph
    """

    _id_counter = 0

    def __init__(self, name: Optional[str] = None):
        # if given a name, then name the apparatus, else default to a sequential name
        if name is not None:
            self.name = name
        else:
            self.name = "DeviceGraph" + str(DeviceGraph._id_counter)
            DeviceGraph._id_counter += 1

        # NetworkX Multi directed graph object
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()

    def add_device(self, device: Any):
        """Add a device or list of devices to the graph"""

        if isinstance(device, Iterable):
            for component in device:
                self._add_device(component)
        else:
            self._add_device(device)

    def _add_device(self, device: Union[Component, Assembly]):
        """Adds a single device to the graph"""
        assert isinstance(device, (Component, Assembly)), "Device must be a Component or a component assembly!"
        self.graph.add_node(device)
        logger.debug(f"Added device <{device.name}> to the device graph {self.name}")

    def add_connection(
        self,
        origin: Union[str, Component],
        destination: Union[str, Component],
        origin_port: Optional[Union[str, int]] = None,
        destination_port: Optional[Union[str, int]] = None,
    ):
        """
        Add a connection to the graph, given either names or objects to be linked.

        Note: if strings are passed for origin/destination, the corresponding node MUST already be part of the graph!
        Note: if the origin or destination are Component instances that are not yet part of the graph,
              they will be added to the graph.
        """

        # If device names are passed, get the device objects
        try:
            if isinstance(origin, str):
                origin = self[origin]
                assert isinstance(origin, Component), "Origin must be a Component!"
            if isinstance(destination, str):
                destination = self[destination]
                assert isinstance(destination, Component), "Destination must be a Component!"
        except KeyError as ke:
            logger.exception(
                "A connection was attempted by node name with nodes that are not part of the graph!"
            )
            raise InvalidConfiguration("Invalid nodes for connection!") from ke

        # If ports are specified, ensure the values are valid with the respective component
        if origin_port is not None:
            assert isinstance(origin, MultiportComponentMixin), "Only MappedComponents have ports!"
            assert origin_port in origin.port, "The port specified was not found!"

        if destination_port is not None:
            assert isinstance(destination, MultiportComponentMixin), "Only MappedComponents have ports!"
            assert destination_port in destination.port, f"The port {destination_port} was not found in {destination}" \
                                                         f"[ports available are: {destination.port}]!"

        # Add the connection
        self.graph.add_edge(origin, destination, from_port=origin_port, to_port=destination_port)

    def __repr__(self):
        return f"<DeviceGraph {self.name}>"

    def __str__(self):
        return f"DeviceGraph {self.name} with {len(self)} devices."

    def __len__(self):
        return self.graph.number_of_nodes()

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        return True

    def __getitem__(self, item):
        """
        Utility method

        DeviceGraph['name'] gives the device with that name
        DeviceGraph[class] returns a list of devices of that type
        DeviceGraph[device_instance] returns true if the object is part of the graph
        """
        # If a type is passed return devices with that type
        if isinstance(item, type):
            return [device for device in self.graph.nodes if isinstance(device, item)]

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

    def component_from_origin_and_port(self, origin: Component, port: Union[str, int]) -> Component:
        """ Returns the component that is connected to the origin component in the port provided. """

        assert origin in self, "The origin component is not part of the graph!"
        assert isinstance(origin, MultiportComponentMixin), "Only MappedComponents have ports!"

        for _, to_component, data in self.graph.out_edges(origin, data=True):
            if data["from_port"] == port:
                return to_component
        raise KeyError(f"No component connected to port {port}")

    def visualize(self):
        """Visualize the graph"""
        import matplotlib.pyplot as plt

        nx.draw(self.graph, with_labels=True)
        plt.show()

    def explode_all(self):
        """Explode all devices in the graph"""
        # Copy list of nodes to prevent change during iteration
        original_nodes = list(self.graph.nodes)
        for device in original_nodes:
            if hasattr(device, "explode"):
                logger.debug(f"Exploding {device.name}")
                device.explode(self)

    def validate(self) -> bool:
        """Validates the graph. This is called by Protocol when the DeviceGraph is used."""

        # Make sure that all the components are connected
        if not nx.is_weakly_connected(self.graph):
            logger.warning("Not all components connected.")
            return False

        # Check validity of mappings in mapped components
        for mapped_component in self[MultiportComponentMixin]:

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

            # Draw a line after the last tube
            end_section = True if tube is last_tube else False

            tubing_table.add_row(
                from_component.name,
                to_component.name,
                f"{tube.length:~H}",
                f"{tube.ID:~H}",
                f"{tube.OD:~H}",
                f"{tube.volume.to('ml'):.4f~H}",
                tube.material,
                end_section=end_section,
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
    from flowchem.core.graph.parser import parse_graph_file
    graph = parse_graph_file("owen_config2.yml")
    graph.summarize()

    graph.explode_all()
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
