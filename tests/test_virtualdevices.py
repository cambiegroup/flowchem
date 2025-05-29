
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
    pump = api_dev['virtual-ml600']['pump']
    assert pump.put("infuse", params={"rate": "1 ml/min", "volume": "1 ml"})
    assert pump.get("is-pumping").json() in (True, False)
    assert pump.put("withdraw", params={"rate": "0.5 ml/min", "volume": "1 ml"})
    assert pump.put("stop")

    valve = api_dev['virtual-ml600']['valve']
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


def test_virtualBenchtopNMR(api_dev):
    nmr = api_dev['virtual-benchtop-nmr']['nmr-control']
    # Assuming a basic status check since commands are not detailed
    assert "status" in nmr.get("status")


"""
def test_virtualPowerSupply(api_dev):
    ps = api_dev['virtual-power-supply']['powersupply']
    ps.put("power-on")
    ps.put("power-off")


def test_virtualIcIRSpectrometer(api_dev):
    icir = api_dev['Virtual-Icir-Spectometer']['icir']
    # Minimal check as API unclear
    assert isinstance(icir.get("status"), dict)

def test_virtualPhidgetsBubble(api_dev):
    sensor = api_dev['Virtual-Phidgets-Bubble']['bubblesensor']
    assert isinstance(sensor.get("read-bubbles"), int)

def test_virtualPhidgetsPressure(api_dev):
    sensor = api_dev['Virtual-Phidgets-Pressure']['pressuresensor']
    assert isinstance(sensor.get("read-pressure"), float)

def test_virtualPhidgetsPower(api_dev):
    power = api_dev['Virtual-Phidgets-Power']['powersource']
    assert power.get("is-powered") in (True, False)

def test_virtualCVC3000(api_dev):
    cvc = api_dev['Virtual-CVC3000']['cvc']
    cvc.put("power-on")
    assert isinstance(cvc.get("status"), str)
    cvc.put("power-off")

def test_virtualR2(api_dev):
    r2 = api_dev['Virtual-R2']['r2']
    assert "status" in r2.get("status")

def test_virtualR4Heater(api_dev):
    r4 = api_dev['Virtual-R4Heater']['r4']
    assert r4.put("set-temperature", params={"temperature": "70 C"})

def test_virtualViciValve(api_dev):
    valve = api_dev['Virtual-ViciValve']['valve']
    assert valve.put("move-to", params={"position": 2})

def test_myRunzeValve(api_dev):
    valve = api_dev['My-Runzen-Valve']['valve']
    assert valve.put("move-to", params={"position": 3})

"""
