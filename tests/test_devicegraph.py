import pytest
from flowchem.components.stdlib import Component, Tube, Vessel
from flowchem import DeviceGraph
a, b, c, d = [Component() for _ in range(4)]
# t = Tube(length="1 foot", ID="1 in", OD="2 in", material="PVC")


@pytest.fixture
def device_graph():
    return DeviceGraph()


def test_add_single(device_graph):
    device_graph.add_device(a)
    # Contains
    assert a in device_graph
    # Length
    assert len(device_graph) == 1
    # Get by name
    assert device_graph[a.name] == a
    # Get by type
    assert len(device_graph[Component]) == 1
    # Get by value
    assert device_graph[a] == a


def test_add_iterable(device_graph):
    device_graph.add_device([a, b, c])
    assert len(device_graph) == 3
    assert a in device_graph
    assert b in device_graph
    assert c in device_graph


def test_add_errors(device_graph):

    # Not a component
    with pytest.raises(AssertionError):
        not_a_component = 5
        device_graph.add_device(not_a_component)

    # Class instead of instance
    with pytest.raises(AssertionError):
        device_graph.add_device(Component)


def test_add_edge(device_graph):
    device_graph.add_device([a, b])
    device_graph.add_connection(a, b)
    assert len(device_graph) == 2
    assert device_graph.validate()


def test_validation(device_graph):
    device_graph.add_device([a, b, c])
    device_graph.add_connection(a, b)
    # C is not connected to anything
    assert device_graph.validate() is False
    # Now DiGraph is weakly connected
    device_graph.add_connection(b, c)
    assert device_graph.validate() is True
