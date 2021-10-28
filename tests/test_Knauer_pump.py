"""
Knauer pump
Run with python -m pytest ./tests -m KPump and updates pump address below
"""
import asyncio
import math
import sys

import pytest

from flowchem import KnauerPump
from flowchem.devices.Knauer.KnauerPump import KnauerPumpHeads

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.yield_fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def pump():
    """ Change to match your hardware ;) """
    pump = KnauerPump(ip_address="192.168.1.126")
    await pump.initialize()
    return pump


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_pumphead(pump: KnauerPump):
    assert await pump.get_headtype() in KnauerPumpHeads
    await pump.set_headtype(KnauerPumpHeads.FLOWRATE_TEN_ML)
    assert await pump.get_headtype() == KnauerPumpHeads.FLOWRATE_TEN_ML
    await pump.set_headtype(KnauerPumpHeads.FLOWRATE_FIFTY_ML)
    assert await pump.get_headtype() == KnauerPumpHeads.FLOWRATE_FIFTY_ML


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_pumphead(pump: KnauerPump):
    assert await pump.get_headtype() in KnauerPumpHeads


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_flow_rate(pump: KnauerPump):
    await pump.set_flow(1.25)
    assert await pump.get_flow() == 1.25
    await pump.set_flow(math.pi)
    assert math.isclose(await pump.get_flow(), math.pi, abs_tol=1e-3)


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_analog_control(pump: KnauerPump):
    await pump.enable_analog_control(True)
    assert await pump.is_analog_control_enabled() is True
    await pump.enable_analog_control(False)
    assert await pump.is_analog_control_enabled() is False


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_is_running(pump: KnauerPump):
    await pump.set_flow(1)
    await pump.start_flow()
    assert pump.is_running() is True
    await pump.stop_flow()


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_is_running(pump: KnauerPump):
    await pump.set_flow(1)
    await pump.start_flow()
    assert pump.is_running() is True
    await pump.stop_flow()


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_motor_current(pump: KnauerPump):
    await pump.stop_flow()
    assert await pump.read_motor_current() == 0
    await pump.set_flow(1)
    await pump.start_flow()
    assert await pump.read_motor_current() > 0
    await pump.stop_flow()


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_correction_factor(pump: KnauerPump):
    init_val = await pump.get_correction_factor()
    await pump.set_correction_factor(0)
    assert await pump.get_correction_factor() == 0
    await pump.set_correction_factor(init_val)


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_adjusting_factor(pump: KnauerPump):
    init_val = await pump.get_adjusting_factor()
    await pump.set_adjusting_factor(0)
    assert await pump.get_adjusting_factor() == 0
    await pump.set_adjusting_factor(init_val)


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_autostart(pump: KnauerPump):
    await pump.enable_autostart()
    assert pump.is_autostart_enabled() is True
    await pump.enable_autostart(False)


@pytest.mark.KPump
@pytest.mark.asyncio
async def test_start_in(pump: KnauerPump):
    await pump.require_start_in()
    assert pump.is_start_in_required() is True
    await pump.require_start_in(False)
