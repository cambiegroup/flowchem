"""
Knauer pump
Run with python -m pytest ./tests -m KPump and updates pump address below
"""
import asyncio
import pytest
import sys

from flowchem import KnauerPump

from flowchem.constants import DeviceError
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
