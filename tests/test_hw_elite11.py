import pytest
import time
from flowchem.devices.Harvard_Apparatus.HA_elite11 import PumpIO, Elite11, PumpStatus


def move_infuse(pump):
    pump.diameter = 10
    pump.infusion_rate = 1
    pump.infuse_run()


@pytest.fixture(scope="session")
def pump():
    """ Pump with address 9 on COM 5. Change to match your hardware ;) """
    serial_pump_chain = PumpIO("COM5")
    return Elite11(serial_pump_chain, 9)


def test_version(pump: Elite11):
    assert "11 ELITE" in pump.version


def test_status_idle(pump: Elite11):
    pump.stop()
    assert pump.get_status() is PumpStatus.IDLE


def test_status_infusing(pump: Elite11):
    move_infuse(pump)
    assert pump.get_status() is PumpStatus.INFUSING
    pump.stop()


def test_status_withdrawing(pump: Elite11):
    pump.diameter = 10
    pump.withdrawing_rate = 1
    pump.withdraw_run()
    assert pump.get_status() is PumpStatus.WITHDRAWING
    pump.stop()


def test_is_moving(pump: Elite11):
    assert pump.is_moving() is False
    move_infuse(pump)
    assert pump.is_moving() is True
    pump.stop()


def test_syringe_volume(pump: Elite11):
    import math
    assert isinstance(pump.syringe_volume, (float, int))
    pump.syringe_volume = 10
    assert pump.syringe_volume == 10
    pump.syringe_volume = math.pi
    assert math.isclose(pump.syringe_volume, math.pi, rel_tol=10e-4)


def test_infusion_rate(pump: Elite11):
    pump.diameter = 10
    pump.infusion_rate = 5
    assert pump.infusion_rate == 5
    with pytest.warns(UserWarning):
        pump.infusion_rate = 121
    assert pump.infusion_rate == 12.4882


