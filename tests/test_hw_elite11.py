"""
HA Elite11 tests
Run with python -m pytest ./tests -m HApump and updates pump com port and address in pump below
"""
import asyncio
import math

import pytest

from flowchem.devices.Harvard_Apparatus.HA_elite11 import (
    Elite11,
    PumpStatus
)
from flowchem.exceptions import DeviceError


async def move_infuse(pump):
    await pump.set_syringe_diameter(10)
    await pump.set_infusion_rate(1)
    await pump.set_target_volume(1)
    await pump.infuse_run()


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def pump():
    """ Change to match your hardware ;) """
    pump = Elite11.from_config(port="COM4", address=6, syringe_volume=5, diameter=20)
    await pump.initialize()
    return pump


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_version(pump: Elite11):
    assert "11 ELITE" in await pump.version()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_status_idle(pump: Elite11):
    await pump.stop()
    assert await pump.get_status() is PumpStatus.IDLE


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_status_infusing(pump: Elite11):
    await move_infuse(pump)
    assert await pump.get_status() is PumpStatus.INFUSING
    await pump.stop()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_status_withdrawing(pump: Elite11):
    await pump.set_syringe_diameter(10)
    await pump.set_withdrawing_rate(1)
    await pump.withdraw_run()
    assert await pump.get_status() is PumpStatus.WITHDRAWING
    await pump.stop()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_is_moving(pump: Elite11):
    assert await pump.is_moving() is False
    await move_infuse(pump)
    assert await pump.is_moving() is True
    await pump.stop()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_syringe_volume(pump: Elite11):
    assert isinstance(await pump.get_syringe_volume(), (float, int))
    await pump.set_syringe_volume(10)
    assert await pump.get_syringe_volume() == 10
    await pump.set_syringe_volume(math.pi)
    assert math.isclose(await pump.get_syringe_volume(), math.pi, abs_tol=10e-4)
    await pump.set_syringe_volume(3.2e-05)
    assert math.isclose(await pump.get_syringe_volume(), 3.2e-5)
    await pump.set_syringe_volume(50)  # Leave a sensible value otherwise other tests will fail!


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_infusion_rate(pump: Elite11):
    await pump.set_syringe_diameter(10)
    await pump.set_infusion_rate(5)
    assert await pump.get_infusion_rate()
    with pytest.warns(UserWarning):
        await pump.set_infusion_rate(121)
    assert math.isclose(await pump.get_infusion_rate(), 12.49, rel_tol=0.01)
    with pytest.warns(UserWarning):
        await pump.set_infusion_rate(0)
    assert math.isclose(await pump.get_infusion_rate(), 1e-05, abs_tol=1e-5)
    await pump.set_infusion_rate(math.pi)
    assert math.isclose(await pump.get_infusion_rate(), math.pi, abs_tol=0.001)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_get_infused_volume(pump: Elite11):
    await pump.clear_volumes()
    assert await pump.get_infused_volume() == 0
    await pump.set_syringe_diameter(30)
    await pump.set_infusion_rate(5)
    await pump.set_target_volume(0.05)
    await pump.infuse_run()
    await asyncio.sleep(2)
    assert math.isclose(await pump.get_infused_volume(), 0.05, abs_tol=1e-4)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_get_withdrawn_volume(pump: Elite11):
    await pump.clear_volumes()
    await pump.set_withdrawing_rate(10)
    await pump.set_target_volume(0.1)
    await pump.withdraw_run()
    await asyncio.sleep(1)
    assert await pump.get_withdrawn_volume() == 0.1


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_force(pump: Elite11):
    await pump.set_force(10)
    assert await pump.get_force() == 10
    await pump.set_force(50.2)
    assert await pump.get_force() == 50
    with pytest.raises(DeviceError) as exception_info:
        await pump.set_force(110)
    assert "Out of range" in str(exception_info.value)
    assert await pump.get_force() == 50


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_diameter(pump: Elite11):
    await pump.set_syringe_diameter(10)
    assert await pump.get_syringe_diameter() == 10

    with pytest.warns(UserWarning):
        await pump.set_syringe_diameter(34)

    with pytest.warns(UserWarning):
        await pump.set_syringe_diameter(0.01)

    await pump.set_syringe_diameter(math.pi)
    math.isclose(await pump.get_syringe_diameter(), math.pi)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_target_volume(pump: Elite11):
    await pump.set_syringe_volume(10)
    await pump.set_target_volume(math.pi)
    assert math.isclose(await pump.get_target_volume(), math.pi, abs_tol=10e-4)
    await pump.set_target_volume(1e-04)
    assert math.isclose(await pump.get_target_volume(), 1e-4, abs_tol=10e-4)
