from typing import List, Tuple, Sequence

from components.properties import MappedComponentMixin
from flowchem.core.graph import DeviceGraph
from flowchem.components.properties import Component


class Assembly(MappedComponentMixin, Component):
    """
    A class representing a collection of components.
    """
    nodes = Sequence[Component]
    edges = Sequence[Tuple[Component, Component]]

    def _subcomponent_by_name(self, name:str) -> Component:
        """ Returns a component in self.nodes by its name. """
        for node in self.nodes:
            if node.name == name:
                return node
        raise ValueError(f"No component named {name} in {self}")

    def _explode(self, graph: DeviceGraph):
        """
        Explode the assembly into its components in the provided graph.
        The graph must already include the assembly as a node with all the connections defined.
        """

        assert self in graph.graph.nodes, "Assembly must be in the graph to explode it."

        # Convert edges to self into edges to self's components.
        in_edges = list(graph.graph.in_edges(self))
        out_edges = list(graph.graph.out_edges(self))
        assert len(in_edges) + len(out_edges) == len(self.mapping), "Assembly has invalid edges."

        for from_component, to_component in in_edges:
            assert to_component is self, "In edges are edges pointing to the current node!"
            # Find edge position in assembly mapping
            position = self.reversed_mapping[from_component]
            # Add edge to assembly's component
            self.edges.append((from_component, self._subcomponent_by_name(position)))

        for from_component, to_component in out_edges:
            assert from_component is self, "Out edges are edges pointing from the current node!"
            # Find edge position in assembly mapping
            position = self.reversed_mapping[to_component]
            # Add edge to assembly's component
            self.edges.append((self._subcomponent_by_name(position), to_component))

        # Updates component names. This ensures unique names in the graph.
        for component in self.nodes:
            component.name = f"{self.name}_{component.name}"

        # Remove assembly from graph (this also removes all edges)
        graph.graph.remove_node(self)

        # Add nodes to graph
        graph.add_device(self.nodes)
        # Add edges to graph
        for edge in self.edges:
            graph.add_connection(edge[0], edge[1])

    def _validate(self, dry_run):
        """Components are valid for dry runs, but not for real runs."""
        raise NotImplementedError("Assembly object should be expanded into their components before run.")
