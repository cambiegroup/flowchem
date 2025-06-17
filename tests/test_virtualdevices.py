import sys
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest

@pytest.fixture(scope="module")
def api_dev(xprocess):
    config_file = Path(__file__).parent.resolve() / "virtualdevices.toml"
    main = Path(__file__).parent.resolve() / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        pattern = "Uvicorn running"
        timeout = 30
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    yield get_all_flowchem_devices()
    xprocess.getinfo("flowchem_instance").terminate()


def test_virtualEPC(api_dev):
    EPC = api_dev['virtual-EPC']['EPC']
    EPC.put("power-on")
    EPC.put("power-off")
    assert EPC.put("set-pressure", params={"pressure": "1 bar"})
    read = EPC.get("read-pressure", params={"units": "bar"}).json()
    assert read["_magnitude"] == 1
    assert EPC.get("get-pressure").json() == 1
    assert EPC.put("stop")


def test_virtualMFC(api_dev):
    MFC = api_dev['virtual-MFC']['MFC']
    assert MFC.put("set-flow-rate", params={"flowrate": "2 ml/min"})
    read = MFC.get("get-flow-rate").json()
    assert read == 2
    assert MFC.put("stop")


def test_virtualPeltier(api_dev):
    TC = api_dev['virtual-peltier']['temperature_control']
    TC.put("power-on")
    TC.put("power-off")
    assert TC.put("temperature", params={"temperature": "25 °C"})
    assert isinstance(TC.get("temperature").json(), (int, float))
    assert TC.get("target-reached").json() in (True, False, None)


def test_virtualML600(api_dev):
    pump = api_dev['virtual-ml600']['left_pump']
    assert pump.put("infuse", params={"rate": "1 ml/min", "volume": "1 ml"})
    assert pump.get("is-pumping").json() in (True, False)
    assert pump.put("withdraw", params={"rate": "0.5 ml/min", "volume": "1 ml"})
    assert pump.put("stop")
    valve = api_dev['virtual-ml600']['left_valve']
    assert isinstance(valve.get("position").json(), list)
    assert valve.put("position", params={"connect": "[[3, 0]]"})


def test_virtualHPLC(api_dev):
    clarity = api_dev['virtual-hplc']['clarity']
    assert clarity.put("send-method", params={"method-name": "Method1.MET"})
    assert clarity.put("run-sample", params={"sample-name": "Sample1", "method-name": "Method1.MET"})
    assert clarity.put("exit")


def test_virtualElite11(api_dev):
    pump = api_dev['virtual-elite11']['pump']
    assert pump.put("infuse", params={"rate": "1 ml/min", "volume": "0.5 ml"})
    assert pump.put("withdraw", params={"rate": "1 ml/min", "volume": "0.3 ml"})
    assert pump.get("is-pumping").json() in (True, False)
    assert pump.put("stop")


def test_virtualHuber(api_dev):
    TC = api_dev['virtual-huber']['temperature-control']
    TC.put("power-on")
    assert TC.put("temperature", params={"temp": "10 °C"})
    assert isinstance(TC.get("temperature").json(), (int, float))
    assert TC.get("target-reached").json() in (True, False)
    TC.put("power-off")


def test_virtualAzura(api_dev):
    pump = api_dev['virtual-azura']['pump']
    assert pump.put("infuse", params={"rate": "2 ml/min", "volume": "3 ml"})
    assert pump.put("stop")
    assert pump.get("is-pumping").json() in (True, False)

    pressure = api_dev['virtual-azura']['pressure']
    pressure.put("power-on")
    assert isinstance(pressure.get("read-pressure", params={"units": "bar"}).json() , (int, float))
    pressure.put("power-off")


def test_virtualKnauerDad(api_dev):
    dad = api_dev['virtual-knauerDad']['d2']
    dad.put("power-on")
    assert dad.get("lamp_status").json() in ("LAMP_D2:0", "LAMP_D2:1")
    assert isinstance(dad.get("status").json(), str)
    dad.put("power-off")


def test_virtualValveKnauer(api_dev):
    valve = api_dev['virtual-valveKnauer']['injection-valve']
    assert valve.put("monitor_position", params={"position": "LOAD"})
    assert valve.get("monitor_position").json() == "LOAD"

###
def test_virtualBenchtopNMR(api_dev):
    nmr = api_dev['virtual-benchtop-nmr']['nmr-control']
    assert nmr.get("is-busy")


def test_virtualPowerSupply(api_dev):
    ps = api_dev['virtual-power-supply']['power-control']
    ps.put("power-on")
    ps.put("power-off")
    ps.put("current", params={"current": 2})
    assert ps.get("current").json() == 2
    ps.put("voltage", params={"voltage": 2})
    assert ps.get("voltage").json() == 2


def test_virtualIcIRSpectrometer(api_dev):
    icir = api_dev['virtual-icir-spectometer']['ir-control']
    assert "intensity" in icir.put("acquire-spectrum").json()
    assert icir.put("stop").json()
    icir.get("spectrum-count")


def test_virtualPhidgetsBubble(api_dev):
    sensor = api_dev['virtual-phidgets-bubble']['bubble-sensor']
    assert sensor.put("power-on").json()
    assert sensor.put("power-off").json()
    assert isinstance(sensor.get("read-voltage").json(), (int, float))
    sensor.get("acquire-signal")


def test_virtualPhidgetsPressure(api_dev):
    sensor = api_dev['virtual-phidgets-pressure']['pressure-sensor']
    sensor.put("power-on")
    assert isinstance(sensor.get("read-pressure").json(), (int, float))
    sensor.put("power-off")


def test_virtualPhidgetsPower(api_dev):
    power = api_dev['virtual-phidgets-power']['5V']
    assert power.put("power-on").json()
    assert power.put("power-off").json()


def test_virtualCVC3000(api_dev):
    cvc = api_dev['virtual-cvc3000']['pressure-control']
    cvc.put("power-on")
    cvc.put("pressure", params={"pressure": 3})
    assert cvc.get("pressure").json() == 3
    assert cvc.get("target-reached").json()
    cvc.put("power-off")


def test_virtualR2(api_dev):
    r2 = api_dev['virtual-r2']['PressureSensor']
    assert isinstance(r2.get("read-pressure").json(), (int, float))


def test_virtualR4Heater(api_dev):
    r4 = api_dev['virtual-r4Heater']['reactor1']
    assert r4.put("temperature", params={"temp": "70"})
    assert r4.get("temperature").json() == 70


def test_virtualViciValve(api_dev):
    valve = api_dev['virtual-ViciValve']['injection-valve']
    valve.put("position", params={"connect": "[[2, 3]]"})
    assert [2, 3] in valve.get("position").json()


def test_myRunzeValve(api_dev):
    valve = api_dev['my-runzen-valve']['distribution-valve']
    valve.put("position", params={"connect": "[[2, 0]]"})
    assert [2, 0] in valve.get("position").json()
    valve.put("monitor_position", params={"position": 3})
    assert int(valve.get("monitor_position").json()) == 3
