"""
HA Elite11 tests

1. Update pump serial port and address belo
2. Run with `python -m pytest ./tests -m HApump` from the root folder
"""
import asyncio
import math

import pytest

from flowchem import ureg
from flowchem.devices.harvardapparatus.elite11 import Elite11InfuseWithdraw
from flowchem.devices.harvardapparatus.elite11 import PumpStatus


@pytest.fixture(scope="session")
async def pump():
    """Change to match your hardware ;)"""
    pump = Elite11InfuseWithdraw.from_config(
        port="COM4", syringe_volume="5 ml", syringe_diameter="20 mm"
    )
    await pump.initialize()
    return pump


async def move_infuse(pump):
    await pump.set_syringe_diameter("10 mm")
    await pump.set_flow_rate("1 ml/min")
    await pump.set_target_volume("1 ml")
    await pump.infuse()


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_version(pump: Elite11InfuseWithdraw):
    assert "11 ELITE" in await pump.version()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_status_idle(pump: Elite11InfuseWithdraw):
    await pump.stop()
    assert await pump.get_status() is PumpStatus.IDLE


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_status_infusing(pump: Elite11InfuseWithdraw):
    await move_infuse(pump)
    assert await pump.get_status() is PumpStatus.INFUSING
    await pump.stop()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_status_withdrawing(pump: Elite11InfuseWithdraw):
    await pump.set_syringe_diameter("10 mm")
    await pump.set_withdrawing_flow_rate("1 ml/min")
    await pump.withdraw()
    assert await pump.get_status() is PumpStatus.WITHDRAWING
    await pump.stop()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_is_moving(pump: Elite11InfuseWithdraw):
    assert await pump.is_moving() is False
    await move_infuse(pump)
    assert await pump.is_moving() is True
    await pump.stop()


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_syringe_volume(pump: Elite11InfuseWithdraw):
    await pump.set_syringe_volume("10 ml")
    assert await pump.get_syringe_volume() == "10 ml"
    await pump.set_syringe_volume(f"{math.pi} ml")
    vol = ureg.Quantity(await pump.get_syringe_volume()).magnitude
    assert math.isclose(vol, math.pi, abs_tol=10e-4)
    await pump.set_syringe_volume("3e-05 ml")
    vol = ureg.Quantity(await pump.get_syringe_volume()).magnitude
    assert math.isclose(vol, 3e-5)
    await pump.set_syringe_volume("50 ml")  # Leave it high for next tests


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_infusion_rate(pump: Elite11InfuseWithdraw):
    await pump.set_syringe_volume("10 ml")
    await pump.set_flow_rate("5 ml/min")
    assert await pump.get_flow_rate()
    with pytest.warns(UserWarning):
        await pump.set_flow_rate("121 ml/min")
    rate = ureg.Quantity(await pump.get_flow_rate()).magnitude
    assert math.isclose(rate, 12.49, rel_tol=0.01)
    with pytest.warns(UserWarning):
        await pump.set_flow_rate("0 ml/min")
    rate = ureg.Quantity(await pump.get_flow_rate()).magnitude
    assert math.isclose(rate, 1e-05, abs_tol=1e-5)
    await pump.set_flow_rate(f"{math.pi} ml/min")
    rate = ureg.Quantity(await pump.get_flow_rate()).magnitude
    assert math.isclose(rate, math.pi, abs_tol=0.001)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_get_infused_volume(pump: Elite11InfuseWithdraw):
    await pump.clear_volumes()
    assert await pump.get_infused_volume() == "0 ul"
    await pump.set_syringe_diameter("30 mm")
    await pump.set_flow_rate("5 ml/min")
    await pump.set_target_volume("0.05 ml")
    await pump.infuse()
    await asyncio.sleep(2)
    vol = ureg.Quantity(await pump.get_infused_volume()).to("ml").magnitude
    assert math.isclose(vol, 0.05, abs_tol=1e-4)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_get_withdrawn_volume(pump: Elite11InfuseWithdraw):
    await pump.clear_volumes()
    await pump.set_withdrawing_flow_rate("10 ml/min")
    await pump.set_target_volume("0.1 ml")
    await pump.withdraw()
    await asyncio.sleep(1)
    vol = ureg.Quantity(await pump.get_withdrawn_volume()).to("ml").magnitude
    assert math.isclose(vol, 0.1, abs_tol=1e-4)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_force(pump: Elite11InfuseWithdraw):
    await pump.set_force(10)
    assert await pump.get_force() == 10
    await pump.set_force(50.2)
    assert await pump.get_force() == 50
    assert await pump.get_force() == 50


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_diameter(pump: Elite11InfuseWithdraw):
    await pump.set_syringe_diameter("10 mm")
    assert await pump.get_syringe_diameter() == "10.0000 mm"

    with pytest.warns(UserWarning):
        await pump.set_syringe_diameter("34 mm")

    with pytest.warns(UserWarning):
        await pump.set_syringe_diameter("0.01 mm")

    await pump.set_syringe_diameter(f"{math.pi} mm")
    dia = ureg.Quantity(await pump.get_syringe_diameter()).magnitude
    math.isclose(dia, math.pi)


@pytest.mark.HApump
@pytest.mark.asyncio
async def test_target_volume(pump: Elite11InfuseWithdraw):
    await pump.set_syringe_volume("10 ml")
    await pump.set_target_volume(f"{math.pi} ml")
    vol = ureg.Quantity(await pump.get_target_volume()).magnitude
    assert math.isclose(vol, math.pi, abs_tol=10e-4)
    await pump.set_target_volume("1e-04 ml")
    vol = ureg.Quantity(await pump.get_target_volume()).magnitude
    assert math.isclose(vol, 1e-4, abs_tol=10e-4)
