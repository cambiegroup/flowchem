""" Test HuberChiller object. Does not require physical connection to the device. """
import asyncio

import aioserial
import pytest

from flowchem.devices.huber import HuberChiller
from flowchem.exceptions import InvalidConfiguration


def test_pbcommand_parse_temp():
    assert (
        HuberChiller.PBCommand("{S00F2DF").parse_temperature()
        == -33.61
    )
    assert (
        HuberChiller.PBCommand("{S0004DA").parse_temperature() == 12.42
    )


def test_pbcommand_parse_int():
    assert HuberChiller.PBCommand("{S000000").parse_integer() == 0
    assert HuberChiller.PBCommand("{S00ffff").parse_integer() == 65535
    assert HuberChiller.PBCommand("{S001234").parse_integer() == 4660


def test_pbcommand_parse_bits():
    assert HuberChiller.PBCommand("{S001234").parse_bits() == [
        False,
        False,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
        False,
        True,
        True,
        False,
        True,
        False,
        False,
    ]


def test_pbcommand_parse_bool():
    assert HuberChiller.PBCommand("{S000001").parse_boolean() is True
    assert HuberChiller.PBCommand("{S000000").parse_boolean() is False


def test_invalid_serial_port():
    with pytest.raises(InvalidConfiguration) as execinfo:
        HuberChiller.from_config(port="COM99")
    assert (
        str(execinfo.value) == "Cannot connect to the HuberChiller on the port <COM99>"
    )


class FakeSerial(aioserial.AioSerial):
    """Mock AioSerial."""

    # noinspection PyMissingConstructor
    def __init__(self):
        self.fixed_reply = None
        self.last_command = b""
        self.map_reply = {
            b"{M0A****\r\n": b"{S0AFFFF\r\n",  # Fake status reply
            b"{M3C****\r\n": b"{S3CFFFF\r\n",  # Fake status2 reply
            b"{M3A****\r\n": b"{S3A04DA\r\n",  # Fake process temperature reply
            b"{M00****\r\n": b"{S0004DA\r\n",  # Fake setpoint reply
            b"{M03****\r\n": b"{S030a00\r\n",  # Fake pressure reply
            b"{M04****\r\n": b"{S04000a\r\n",  # Fake current power reply (10 W)
            b"{M26****\r\n": b"{S26000a\r\n",  # Fake current pump speed (10 rpm)
            b"{M30****\r\n": b"{S30EC78\r\n",  # Fake min temp -50.00 C
            b"{M31****\r\n": b"{S303A98\r\n",  # Fake max temp +150.00 C
            b"{M00EC78\r\n": b"{S00EC78\r\n",  # set temp to -50
            b"{M003A98\r\n": b"{S003A98\r\n",  # set temp to 150
            b"{M0007D0\r\n": b"{S0007D0\r\n",  # Reply to set temp 20 C
            b"{M00F830\r\n": b"{S00F830\r\n",  # Reply to set temp -20 C
        }

    async def write_async(self, text: bytes):
        """Override AioSerial method"""
        self.last_command = text

    async def readline_async(self, size: int = -1) -> bytes:
        """Override AioSerial method"""
        if self.last_command == b"{MFFFFFF\r\n":
            await asyncio.sleep(999)
        if self.fixed_reply:
            return self.fixed_reply
        return self.map_reply[self.last_command]

    def __repr__(self):
        return "FakeSerial"


@pytest.fixture(scope="session")
def chiller():
    """Chiller instance connected to FakeSerial"""
    return HuberChiller(FakeSerial())


@pytest.mark.asyncio
async def test_no_reply(chiller):
    with pytest.warns(UserWarning):
        reply = await chiller._send_command_and_read_reply("{MFFFFFF")
    assert reply == "{SFFFFFF"


@pytest.mark.asyncio
async def test_status(chiller):
    chiller._serial.fixed_reply = None
    stat = await chiller.status()
    stat_content = list(stat.values())
    assert all(stat_content)

    # Set reply in FakeSerial
    chiller._serial.fixed_reply = b"{S0A0000"
    stat = await chiller.status()
    stat_content = list(stat.values())
    assert not any(stat_content)


@pytest.mark.asyncio
async def test_status2(chiller):
    chiller._serial.fixed_reply = None
    stat = await chiller.status2()
    stat_content = [x for x in stat.values()]
    assert all(stat_content)

    # Set reply in FakeSerial
    chiller._serial.fixed_reply = b"{S0A0000"
    stat = await chiller.status2()
    stat_content = [x for x in stat.values()]
    assert not any(stat_content)


@pytest.mark.asyncio
async def test_get_temperature_setpoint(chiller):
    chiller._serial.fixed_reply = None

    temp = await chiller.get_temperature()
    assert temp == 12.42

    chiller._serial.fixed_reply = b"{S00F2DF"
    temp = await chiller.get_temperature()
    assert temp == -33.61


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_set_temperature_setpoint(chiller):
    chiller._serial.fixed_reply = None
    await chiller.set_temperature("20 °C")
    print(chiller._serial.last_command)
    assert chiller._serial.last_command == b"{M0007D0\r\n"

    await chiller.set_temperature("-20 °C")
    assert chiller._serial.last_command == b"{M00F830\r\n"

    with pytest.warns(Warning):
        await chiller.set_temperature("-400 °C")
        assert chiller._serial.last_command == b"{M00EC78\r\n"

    with pytest.warns(Warning):
        await chiller.set_temperature("4000 °C")
        assert chiller._serial.last_command == b"{M003A98\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_internal_temperature(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.internal_temperature()
    assert chiller._serial.last_command == b"{M01****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_return_temperature(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.return_temperature()
    assert chiller._serial.last_command == b"{M02****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_process_temperature(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.process_temperature()
    assert chiller._serial.last_command == b"{M3A****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_pump_pressure(chiller):
    chiller._serial.fixed_reply = None
    pressure = await chiller.pump_pressure()
    assert chiller._serial.last_command == b"{M03****\r\n"
    assert pressure == "2560 millibar"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_current_power(chiller):
    chiller._serial.fixed_reply = None
    power = await chiller.current_power()
    assert chiller._serial.last_command == b"{M04****\r\n"
    assert power == "10 watt"


@pytest.mark.asyncio
async def test_get_temperature_control(chiller):
    chiller._serial.fixed_reply = b"{S140000"
    t_ctl = await chiller.is_temperature_control_active()
    assert t_ctl is False
    chiller._serial.fixed_reply = b"{S140001"
    t_ctl = await chiller.is_temperature_control_active()
    assert t_ctl is True


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_temperature_control(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.power_on()
    assert chiller._serial.last_command == b"{M140001\r\n"
    await chiller.power_off()
    assert chiller._serial.last_command == b"{M140000\r\n"


@pytest.mark.asyncio
async def test_get_circulation(chiller):
    chiller._serial.fixed_reply = b"{S160000"
    circulation = await chiller.is_circulation_active()
    assert circulation is False
    chiller._serial.fixed_reply = b"{S160001"
    circulation = await chiller.is_circulation_active()
    assert circulation is True


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_circulation(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.start_circulation()
    assert chiller._serial.last_command == b"{M160001\r\n"
    await chiller.stop_circulation()
    assert chiller._serial.last_command == b"{M160000\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_pump_speed(chiller):
    chiller._serial.fixed_reply = None
    speed = await chiller.pump_speed()
    assert chiller._serial.last_command == b"{M26****\r\n"
    assert speed == "10 revolutions_per_minute"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_pump_speed_setpoint(chiller):
    chiller._serial.fixed_reply = b"{S480000"
    speed = await chiller.pump_speed_setpoint()
    assert chiller._serial.last_command == b"{M48****\r\n"
    assert speed == "0 revolutions_per_minute"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_set_pump_speed(chiller):
    chiller._serial.fixed_reply = b"{S480000"
    await chiller.set_pump_speed("10 rpm")
    assert chiller._serial.last_command == b"{M48000A\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_cooling_water_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.cooling_water_temp()
    assert chiller._serial.last_command == b"{M2C****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_cooling_water_pressure(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.cooling_water_pressure()
    assert chiller._serial.last_command == b"{M2D****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_cooling_water_temp_out(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.cooling_water_temp_outflow()
    assert chiller._serial.last_command == b"{M4C****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_alarm_max_internal_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.alarm_max_internal_temp()
    assert chiller._serial.last_command == b"{M51****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_alarm_min_internal_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.alarm_min_internal_temp()
    assert chiller._serial.last_command == b"{M52****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_alarm_max_process_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.alarm_max_process_temp()
    assert chiller._serial.last_command == b"{M53****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_alarm_min_process_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.alarm_min_process_temp()
    assert chiller._serial.last_command == b"{M54****\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_set_alarm_max_internal_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.set_alarm_max_internal_temp("10 °C")
    assert chiller._serial.last_command == b"{M5103E8\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_set_alarm_min_internal_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.set_alarm_min_internal_temp("10 °C")
    assert chiller._serial.last_command == b"{M5203E8\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_set_alarm_max_process_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.set_alarm_max_process_temp("10 °C")
    assert chiller._serial.last_command == b"{M5303E8\r\n"


# noinspection PyUnresolvedReferences
@pytest.mark.asyncio
async def test_set_alarm_min_process_temp(chiller):
    chiller._serial.fixed_reply = b"{S000000"
    await chiller.set_alarm_min_process_temp("10 °C")
    assert chiller._serial.last_command == b"{M5403E8\r\n"
