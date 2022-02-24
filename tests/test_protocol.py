from datetime import timedelta

import pytest


from flowchem import DeviceGraph, Protocol
from flowchem.components.properties import Valve, Component
from flowchem.components.dummy import Dummy
from flowchem.components.stdlib import Pump, Vessel


@pytest.fixture
def device_graph():
    D = DeviceGraph()
    a, b = [Component() for _ in range(2)]
    pump = Pump("pump")
    D.add_device([a, b, pump])
    D.add_connection(a, b)
    D.add_connection(b, pump)
    return D


def test_create_protocol(device_graph):
    # test naming
    assert Protocol(device_graph, name="testing").name == "testing"
    assert Protocol(device_graph).name == "Protocol_0"
    assert Protocol(device_graph).name == "Protocol_1"


def test_add(device_graph):
    P = Protocol(device_graph)

    procedure = {
        "component": device_graph["pump"],
        "params": {"rate": "10 mL/min"},
        "start": 0,
        "stop": 300,
    }

    # test using duration
    P.add(device_graph["pump"], rate="10 mL/min", duration="5 min")
    assert P.procedures[0] == procedure

    # test adding with start and stop
    P.procedures = []
    P.add(device_graph["pump"], rate="10 mL/min", start="0 min", stop="5 min")
    assert P.procedures[0] == procedure

    # test adding with start and stop as timedeltas
    P.procedures = []
    P.add(
        device_graph["pump"], rate="10 mL/min", start=timedelta(seconds=0), stop=timedelta(minutes=5)
    )
    assert P.procedures[0] == procedure

    # test adding with duration as timedelta
    P.procedures = []
    P.add(device_graph["pump"], rate="10 mL/min", duration=timedelta(minutes=5))
    assert P.procedures[0] == procedure

    P = Protocol(device_graph)
    with pytest.raises(AssertionError):
        P.add(Pump("not in apparatus"), rate="10 mL/min", duration="5 min")

    # adding a class, not an instance of it
    with pytest.raises(ValueError):
        P.add(Pump, rate="10 mL/min", duration="5 min")

    # Not adding keyword args
    with pytest.raises(RuntimeError):
        P.add(device_graph["pump"], duration="5 min")

    # Invalid keyword for component
    with pytest.raises(ValueError):
        P.add(device_graph["pump"], active=False, duration="5 min")

    # Invalid dimensionality for kwarg
    with pytest.raises(ValueError):
        P.add(device_graph["pump"], rate="5 mL", duration="5 min")

    # No unit
    with pytest.raises(ValueError):
        P.add(device_graph["pump"], rate="5", duration="5 min")

    # Just the raw value without a unit
    with pytest.raises(ValueError):
        P.add(device_graph["pump"], rate=5, duration="5 min")

    # Providing stop and duration should raise error
    with pytest.raises(RuntimeError):
        P.add(device_graph["pump"], rate="5 mL/min", stop="5 min", duration="5 min")

    # stop time before start time
    with pytest.raises(ValueError):
        P.add([device_graph["pump"],  device_graph["pump"]], rate="10 mL/min", start="5 min", stop="4 min")


def test_add_dummy(device_graph):
    dummy = Dummy(name="dummy")
    device_graph.add_connection(dummy, "pump")
    P = Protocol(device_graph)
    with pytest.raises(ValueError):
        P.add(dummy, active=1)  # should be a bool!


# def test_add_valve(device_graph):
#     valve = Valve(port={1, 2})
#     bad_valve = Valve(port={1, 2})
#     pump1 = Pump("pump1")
#     pump2 = Pump("pump2")
#
#     device_graph.add_connection(valve, "pump", 2)
#     device_graph.add_connection(valve, pump1, 1)
#     device_graph.add_connection(bad_valve, "pump", 1)
#     device_graph.add_connection(bad_valve, pump2, 2)
#     P = Protocol(device_graph)
#
#     expected = [dict(start=0, stop=1, component=valve, params={"setting": 1})]
#
#     # directly pass the pump object
#     P.add(valve, setting=pump1, duration="1 sec")
#     assert P.procedures == expected
#     P.procedures = []
#
#     # using its name
#     P.add(valve, setting="pump1", duration="1 sec")
#     assert P.procedures == expected
#     P.procedures = []
#
#     # using its port number
#     P.add(valve, setting=1, duration="1 sec")
#     assert P.procedures == expected
#
#     with pytest.raises(ValueError):
#         P.add(valve, setting=3, duration="1 sec")
#
#     with pytest.raises(ValueError):
#         P.add(bad_valve, setting=3, duration="1 sec")


# def test_compile():
#     P = Protocol(A)
#     P.add([pump1, pump2], rate="10 mL/min", duration="5 min")
#     assert P._compile() == {
#         pump1: [
#             {"params": {"rate": "10 mL/min"}, "time": 0},
#             {"params": {"rate": "0 mL/min"}, "time": 300},
#         ],
#         pump2: [
#             {
#                 "params": {"rate": "10 mL/min"},
#                 "time": flowchem_ureg.parse_expression("0 seconds"),
#             },
#             {"params": {"rate": "0 mL/min"}, "time": 300},
#         ],
#     }
#
#
# def test_unused_component():
#     # raise warning if component not used
#     P = Protocol(A)
#     P.add(pump1, rate="10 mL/min", duration="5 min")
#     with pytest.warns(UserWarning, match="not used"):
#         P._compile()
#
#
# def test_switching_rates():
#     # check switching between rates
#     P = Protocol(A)
#     P.add([pump1, pump2], rate="10 mL/min", duration="5 min")
#     P.add(pump1, rate="5 mL/min", start="5 min", stop="10 min")
#     assert P._compile() == {
#         pump1: [
#             {"params": {"rate": "10 mL/min"}, "time": 0},
#             {"params": {"rate": "5 mL/min"}, "time": 300},
#             {"params": {"rate": "0 mL/min"}, "time": 600},
#         ],
#         pump2: [
#             {"params": {"rate": "10 mL/min"}, "time": 0},
#             {"params": {"rate": "0 mL/min"}, "time": 300},
#         ],
#     }
#
#
# def test_overlapping_procedures():
#     P = Protocol(A)
#     P.add(pump1, start="0 seconds", stop="5 seconds", rate="5 mL/min")
#     P.add(pump1, start="2 seconds", stop="5 seconds", rate="2 mL/min")
#     with pytest.raises(RuntimeError):
#         P._compile()
#
#
# def test_conflicting_continuous_procedures():
#     P = Protocol(A)
#     P.add(pump1, rate="5 mL/min", stop="1 sec")
#     P.add(pump1, rate="2 mL/min", stop="1 sec")
#     with pytest.raises(RuntimeError):
#         P._compile()
#
#
# def test_json():
#     P = Protocol(A)
#     P.add([pump1, pump2], rate="10 mL/min", duration="5 min")
#     assert json.loads(P.json()) == [
#         {
#             "start": 0,
#             "stop": 300,
#             "component": "pump1",
#             "params": {"rate": "10 mL/min"},
#         },
#         {
#             "start": 0,
#             "stop": 300,
#             "component": "pump2",
#             "params": {"rate": "10 mL/min"},
#         },
#     ]
#
#
# def test_yaml():
#     P = Protocol(A)
#     P.add([pump1, pump2], rate="10 mL/min", duration="5 min")
#     assert yaml.safe_load(P.yaml()) == json.loads(P.json())
