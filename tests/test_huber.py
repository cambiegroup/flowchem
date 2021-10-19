""" Test HuberChiller object. Does not require physical connection to the device. """
import aioserial
import pytest
from flowchem.devices.Huber.huberchiller import HuberChiller, ChillerStatus


class FakeSerial(aioserial.AioSerial):
    """ Mock AioSerial. """

    # noinspection PyMissingConstructor
    def __init__(self):
        self.fixed_reply = None
        self.last_command = b""
        self.map_reply = {
            b"{M0A****\r\n": b"{S0AFFFF\r\n",  # Fake status reply
            b"{M00****\r\n": b"{S0004DA\r\n",  # Fake setpoint reply
            b"{M03****\r\n": b"{S030a00\r\n",  # Fake pressure reply
            b"{M04****\r\n": b"{S04000a\r\n",  # Fake current power reply (10 W)
            b"{M26****\r\n": b"{S26000a\r\n",  # Fake current pump speed (10 rpm)
            b"{M30****\r\n": b"{S30C4F9\r\n",  # Fake min temp -151.11 C
            b"{M31****\r\n": b"{S307530\r\n",  # Fake max temp +300.00 C
            b"{M0007D0\r\n": b"{S0007D0\r\n",  # Reply to set temp 20 C
            b"{M00F830\r\n": b"{S00F830\r\n",  # Reply to set temp -20 C
        }

    async def write_async(self, text: bytes):
        """ Override AioSerial method """
        self.last_command = text

    async def readline_async(self,  size: int = -1) -> bytes:
        """ Override AioSerial method """
        if self.fixed_reply:
            return self.fixed_reply
        return self.map_reply[self.last_command]


@pytest.fixture(scope="session")
def chiller():
    """ Chiller instance connected to FakeSerial """
    return HuberChiller(FakeSerial())


@pytest.mark.asyncio
async def test_status(chiller):
    chiller._serial.fixed_reply = None
    stat = await chiller.status()
    assert stat == ChillerStatus("1111111111111111")

    # Set reply in FakeSerial
    chiller._serial.fixed_reply = b"{S0A0000"
    stat = await chiller.status()
    assert stat == ChillerStatus("0000000000000000")


@pytest.mark.asyncio
async def test_get_temperature_setpoint(chiller):
    chiller._serial.fixed_reply = None
    temp = await chiller.get_temperature_setpoint()
    assert temp == 12.42

    chiller._serial.fixed_reply = b"{S00F2DF"
    temp = await chiller.get_temperature_setpoint()
    assert temp == -33.61


@pytest.mark.asyncio
async def test_set_temperature_setpoint(chiller):
    chiller._serial.fixed_reply = None
    await chiller.set_temperature_setpoint(20)
    assert chiller._serial.last_command == b"{M0007D0\r\n"

    await chiller.set_temperature_setpoint(-20)
    assert chiller._serial.last_command == b"{M00F830\r\n"


@pytest.mark.asyncio
async def test_internal_temperature(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.internal_temperature()
    assert chiller._serial.last_command == b"{M01****\r\n"


@pytest.mark.asyncio
async def test_return_temperature(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.return_temperature()
    assert chiller._serial.last_command == b"{M02****\r\n"


@pytest.mark.asyncio
async def test_pump_pressure(chiller):
    chiller._serial.fixed_reply = None
    pressure = await chiller.pump_pressure()
    assert chiller._serial.last_command == b"{M03****\r\n"
    assert pressure == 1560


@pytest.mark.asyncio
async def test_current_power(chiller):
    chiller._serial.fixed_reply = None
    power = await chiller.current_power()
    assert chiller._serial.last_command == b"{M04****\r\n"
    assert power == 10


@pytest.mark.asyncio
async def test_get_temperature_control(chiller):
    chiller._serial.fixed_reply = b"{S140000"
    t_ctl = await chiller.get_temperature_control()
    assert t_ctl is False
    chiller._serial.fixed_reply = b"{S140001"
    t_ctl = await chiller.get_temperature_control()
    assert t_ctl is True


@pytest.mark.asyncio
async def test_temperature_control(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.start_temperature_control()
    assert chiller._serial.last_command == b"{M140001\r\n"
    await chiller.stop_temperature_control()
    assert chiller._serial.last_command == b"{M140000\r\n"


@pytest.mark.asyncio
async def test_get_circulation(chiller):
    chiller._serial.fixed_reply = b"{S160000"
    circulation = await chiller.get_circulation()
    assert circulation is False
    chiller._serial.fixed_reply = b"{S160001"
    circulation = await chiller.get_circulation()
    assert circulation is True


@pytest.mark.asyncio
async def test_circulation(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.start_circulation()
    assert chiller._serial.last_command == b"{M160001\r\n"
    await chiller.stop_circulation()
    assert chiller._serial.last_command == b"{M160000\r\n"


@pytest.mark.asyncio
async def test_min_setpoint(chiller):
    chiller._serial.fixed_reply = None
    min_t = await chiller.min_setpoint()
    assert min_t == -151.11


@pytest.mark.asyncio
async def test_max_setpoint(chiller):
    chiller._serial.fixed_reply = None
    max_t = await chiller.max_setpoint()
    assert max_t == 300


@pytest.mark.asyncio
async def test_pump_speed(chiller):
    chiller._serial.fixed_reply = None
    speed = await chiller.pump_speed()
    assert chiller._serial.last_command == b"{M26****\r\n"
    assert speed == 10


@pytest.mark.asyncio
async def test_pump_speed_setpoint(chiller):
    chiller._serial.fixed_reply = b"{S480000"
    speed = await chiller.pump_speed_setpoint()
    assert chiller._serial.last_command == b"{M48****\r\n"
    assert speed == 0


@pytest.mark.asyncio
async def test_set_pump_speed(chiller):
    chiller._serial.fixed_reply = b"{S480000"
    await chiller.set_pump_speed(10)
    assert chiller._serial.last_command == b"{M48000A\r\n"


@pytest.mark.asyncio
async def test_cooling_water_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.cooling_water_temp()
    assert chiller._serial.last_command == b"{M2C****\r\n"

@pytest.mark.asyncio
async def test_cooling_water_pressure(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.cooling_water_pressure()
    assert chiller._serial.last_command == b"{M2D****\r\n"
