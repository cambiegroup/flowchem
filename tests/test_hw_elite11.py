import pytest
import time
import math

from flowchem.devices.Harvard_Apparatus.HA_elite11 import PumpIO, Elite11, PumpStatus, InvalidArgument
import logging
logging.basicConfig()
logging.getLogger('flowchem').setLevel(logging.DEBUG)


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
    pump.syringe_volume = 3.2e-09
    assert math.isclose(pump.syringe_volume, 3.2e-9)


def test_infusion_rate(pump: Elite11):
    pump.diameter = 10
    pump.infusion_rate = 5
    assert pump.infusion_rate == 5
    with pytest.warns(UserWarning):
        pump.infusion_rate = 121
    assert pump.infusion_rate == 12.4882
    with pytest.warns(UserWarning):
        pump.infusion_rate = 0
    assert pump.infusion_rate == 1e-05


def test_get_infused_volume(pump: Elite11):
    pump.clear_volumes()
    pump.infusion_rate = 10
    pump.target_volume = 0.1
    pump.infuse_run()
    time.sleep(1)
    assert pump.get_infused_volume() == 0.1


def test_get_withdrawn_volume(pump: Elite11):
    pump.clear_volumes()
    pump.withdrawing_rate = 10
    pump.target_volume = 0.1
    pump.withdraw_run()
    time.sleep(1)
    assert pump.get_withdrawn_volume() == 0.1


def test_force(pump: Elite11):
    pump.force = 10
    assert pump.force == 10
    pump.force = 50.2
    assert pump.force == 50
    with pytest.raises(InvalidArgument) as excinfo:
        pump.force = 110
    assert "Out of range" in str(excinfo.value)
    assert pump.force == 50


def test_diameter(pump: Elite11):
    pump.diameter = 10
    assert pump.diameter == 10

    with pytest.raises(InvalidArgument) as excinfo:
        pump.diameter = 34
    assert "not valid" in str(excinfo.value)

    with pytest.raises(InvalidArgument) as excinfo:
        pump.diameter = 0.01
    assert "not valid" in str(excinfo.value)

    pump.diameter = math.pi
    math.isclose(pump.diameter, math.pi)


def test_target_volume(pump: Elite11):
    pump.target_volume = math.pi
    assert math.isclose(pump.target_volume, math.pi, rel_tol=10e-4)
    pump.target_volume = 1e-04
    assert pump.target_volume == 1e-4
