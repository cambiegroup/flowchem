
from flowchem.components.stdlib import DummyPump, DummySensor, Vessel, BrokenDummySensor, Tube
from flowchem import Protocol, DeviceGraph

# create components
from flowchem.units import flowchem_ureg

#
# def test_execute():
#     a = Vessel(name="a", description="nothing")
#     b = Vessel(name="b", description="nothing")
#     c = Vessel(name="c", description="nothing")
#
#     pump = DummyPump(name="Dummy pump")
#
#     test = DummySensor(name="test")
#     test2 = DummySensor(name="test2")
#     test3 = DummySensor(name="test3")
#     test4 = BrokenDummySensor(name="test4")
#
#     tube = Tube("1 foot", "1/16 in", "2/16 in", "PVC")
#
#     # create apparatus
#     D = DeviceGraph()
#     # A = Apparatus()
#     A.add([a, b, c], pump, tube)
#     A.add(pump, [test, test2, test3, test4], tube)
#
#     P = Protocol(A, name="testing execution")
#     P.add(pump, rate="5 mL/min", start="0 seconds", stop="1 secs")
#     P.add([test, test2, test3, test4], rate="5 Hz", start="0 secs", stop="1 secs")
#
#     # test both execution modes
#     for dry_run in [True, False]:
#         E = P.execute(confirm=True, dry_run=dry_run, log_file=None, data_file=None)
#
#         assert len(E.data["test"]) >= 5
#         if dry_run:
#             assert E.data["test"][0].data == "simulated read"
#         assert pump.rate == flowchem_ureg.parse_expression(pump._base_state["rate"])
#
#     # test fast forward
#     E = P.execute(confirm=True, dry_run=5, log_file=None, data_file=None)
#     assert len(E.data["test"]) >= 1
