"""
HA Elite11 tests
Run with python -m pytest ./tests -m HApump and updates pump com port and address in pump below
"""

import pytest
import time
import math

from flowchem.devices.Harvard_Apparatus.HA_elite11 import (
    PumpIO,
    Elite11,
    PumpStatus
)
from flowchem.constants import DeviceError
import logging

logging.basicConfig()
logging.getLogger("flowchem").setLevel(logging.DEBUG)


def move_infuse(pump):
    pump.set_syringe_diameter(10)
    pump.set_infusion_rate = 1
    pump.infuse_run()


@pytest.fixture(scope="session")
def pump():
    """ Pump with address 9 on COM 5. Change to match your hardware ;) """
    serial_pump_chain = PumpIO("COM5")
    return Elite11(serial_pump_chain, 9)


@pytest.mark.HApump
def test_version(pump: Elite11):
    assert "11 ELITE" in pump.version()


@pytest.mark.HApump
def test_status_idle(pump: Elite11):
    pump.stop()
    assert pump.get_status() is PumpStatus.IDLE


@pytest.mark.HApump
def test_status_infusing(pump: Elite11):
    move_infuse(pump)
    assert pump.get_status() is PumpStatus.INFUSING
    pump.stop()


@pytest.mark.HApump
def test_status_withdrawing(pump: Elite11):
    pump.set_syringe_diameter(10)
    pump.set_withdrawing_rate(1)
    pump.withdraw_run()
    assert pump.get_status() is PumpStatus.WITHDRAWING
    pump.stop()


@pytest.mark.HApump
def test_is_moving(pump: Elite11):
    assert pump.is_moving() is False
    move_infuse(pump)
    assert pump.is_moving() is True
    pump.stop()


@pytest.mark.HApump
def test_syringe_volume(pump: Elite11):
    import math

    assert isinstance(pump.get_syringe_volume(), (float, int))
    pump.set_syringe_volume(10)
    assert pump.get_syringe_volume() == 10
    pump.set_syringe_volume(math.pi)
    assert math.isclose(pump.get_syringe_volume(), math.pi, abs_tol=10e-4)
    pump.set_syringe_volume(3.2e-09)
    assert math.isclose(pump.get_syringe_volume(), 3.2e-9)


@pytest.mark.HApump
def test_infusion_rate(pump: Elite11):
    pump.set_syringe_diameter(10)
    pump.set_infusion_rate(5)
    assert pump.get_infusion_rate()
    with pytest.warns(UserWarning):
        pump.set_infusion_rate(121)
    assert pump.get_infusion_rate() == 12.4882
    with pytest.warns(UserWarning):
        pump.set_infusion_rate(0)
    assert pump.get_infusion_rate() == 1e-05
    pump.set_infusion_rate(math.pi)
    assert math.isclose(pump.get_infusion_rate(), math.pi, abs_tol=0.001)


@pytest.mark.HApump
def test_get_infused_volume(pump: Elite11):
    pump.clear_volumes()
    pump.set_infusion_rate = 10
    pump.target_volume = 0.1
    pump.infuse_run()
    time.sleep(1)
    assert pump.get_infused_volume() == 0.1


@pytest.mark.HApump
def test_get_withdrawn_volume(pump: Elite11):
    pump.clear_volumes()
    pump.set_withdrawing_rate(10)
    pump.target_volume = 0.1
    pump.withdraw_run()
    time.sleep(1)
    assert pump.get_withdrawn_volume() == 0.1


@pytest.mark.HApump
def test_force(pump: Elite11):
    pump.set_force(10)
    assert pump.get_force() == 10
    pump.set_force(50.2)
    assert pump.get_force() == 50
    with pytest.raises(DeviceError) as exception_info:
        pump.set_force(110)
    assert "Out of range" in str(exception_info.value)
    assert pump.get_force() == 50


@pytest.mark.HApump
def test_diameter(pump: Elite11):
    pump.set_syringe_diameter(10)
    assert pump.get_syringe_diameter() == 10

    with pytest.raises(DeviceError) as exception_info:
        pump.set_syringe_diameter(34)
    assert "not valid" in str(exception_info.value)

    with pytest.raises(DeviceError) as exception_info:
        pump.set_syringe_diameter(0.01)
    assert "not valid" in str(exception_info.value)

    pump.set_syringe_diameter(math.pi)
    math.isclose(pump.get_syringe_diameter(), math.pi)


@pytest.mark.HApump
def test_target_volume(pump: Elite11):
    pump.set_target_volume(math.pi)
    assert math.isclose(pump.get_target_volume(), math.pi, abs_tol=10e-4)
    pump.set_target_volume(1e-04)
    assert pump.get_target_volume() == 1e-4
