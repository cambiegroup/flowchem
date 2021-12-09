from flowchem import DeviceGraph


def test_basic_graph():
    test_conf = {
        "version": "1.0",
        "devices": {
            "pump": {"DummyPump": {}},
            "sensor": {"DummySensor": {}},
        },
        "physical_connections": [
            {"Tube": {
                "from": {"device": "pump"},
                "to": {"device": "sensor"},
                "length": "0.1 m",
                "inner-diameter": "0.760 mm",
                "outer-diameter": "1.6 mm",
                "material": "PFA"}
            },
        ]
    }

    D = DeviceGraph(configuration=test_conf, name="test graph")
    nodes = list(D.graph.nodes)
    assert len(nodes) == 3
    edges = list(D.graph.edges)
    assert len(edges) == 2
