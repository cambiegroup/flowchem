from typing import Tuple, Sequence, TYPE_CHECKING

from flowchem.components.properties import MultiportComponentMixin
from flowchem.components.properties import Component

if TYPE_CHECKING:
    from flowchem.core.graph import DeviceGraph


class Assembly(MultiportComponentMixin, Component):
    """ A class representing a collection of components. """
    nodes: Sequence[Component]
    edges: Sequence[Tuple[Component, Component]]

    def _subcomponent_by_name(self, name: str) -> Component:
        """ Returns a component in self.nodes by its name. """
        for node in self.nodes:
            if node.name == name:
                return node
        raise ValueError(f"No component named {name} in {self}")

    def explode(self, graph: "DeviceGraph"):
        """
        Explode the assembly into its components in the provided graph.
        The graph must already include the assembly as a node with all the connections defined.
        """

        assert self in graph.graph.nodes, "Assembly must be in the graph to explode it."

        # Convert edges to self into edges to self's components.
        for from_component, to_component, attributes in graph.graph.in_edges(self, data=True):
            assert to_component is self, "Getting the edges pointing to the assembly."

            # If unspecified, the connection is assumed to all the assembly subcomponents.
            # This should only happen for logical connections (e.g. temp control).
            if attributes["to_port"] is None:
                for to_component in self.nodes:
                    graph.graph.add_edge(from_component, to_component)
                continue

            # New destination is the component with name matching the edge port on the assembly
            new_to_component = self._subcomponent_by_name(attributes["to_port"])

            # Update edge - just add a new one, the old one will be implicitly removed with graph.remove_node(self)
            graph.add_connection(origin=from_component, destination=new_to_component,
                                 origin_port=attributes.get("from_port", None))

        for from_component, to_component, attributes in graph.graph.out_edges(self, data=True):
            assert from_component is self, "Getting the edges pointing from the assembly."

            # New origin is the component with name matching the edge port on the assembly
            new_from_component = self._subcomponent_by_name(attributes["from_port"])

            # Update edge - just add a new one, the old one will be implicitly removed with graph.remove_node(self)
            graph.add_connection(origin=new_from_component, destination=to_component,
                                 destination_port=attributes.get("to_port", None))

        # Updates component names. Ensures unique names in the graph. (Note: do not update those earlier: see above!)
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
