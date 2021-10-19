"""
Driver for Huber chillers.
"""
import logging
import time

import aioserial
import asyncio
from dataclasses import dataclass


class ChillerStatus:
    def __init__(self, bit_values):
        self.temp_ctl_active = bit_values[0] == "1"
        self.circulation_active = bit_values[1] == "1"
        self.refrigerator_on = bit_values[2] == "1"
        self.temp_is_process = bit_values[3] == "1"
        self.circulating_pump = bit_values[4] == "1"
        self.cooling_power_available = bit_values[5] == "1"
        self.tkeylock = bit_values[6] == "1"
        self.is_pid_auto = bit_values[7] == "1"
        self.error = bit_values[8] == "1"
        self.warning = bit_values[9] == "1"
        self.int_temp_mode = bit_values[10] == "1"
        self.ext_temp_mode = bit_values[11] == "1"
        self.dv_e_grade = bit_values[12] == "1"
        self.power_failure = bit_values[13] == "1"
        self.freeze_protection = bit_values[14] == "1"

    def __repr__(self):
        return str(self.__dict__)


@dataclass
class PBCommand:
    """ Class representing a PBCommand """

    command: str

    def to_chiller(self) -> bytes:
        self.validate()
        return self.command.encode("ascii")

    def validate(self):
        """ Check command structure to be compliant with PB format """
        # 10 characters
        assert len(self.command) == 10
        # Starts with {
        assert self.command[0] == "{"
        # M for master (commands) S for slave (replies).
        assert self.command[1] in ("M", "S")
        # Address, i.e. the desired function. Hex encoded.
        assert 0 <= int(self.command[2:4], 16) < 256
        # Value
        assert self.command[4:8] == "****" or 0 <= int(self.command[4:8], 16) <= 65536
        # EOL
        assert self.command[8:10] == "\r\n"

    @property
    def data(self):
        return self.command[4:8]

    @property
    def is_reply(self):
        return self.command[1] == "S"

    def parse_temperature(self):
        # convert two's complement 16 bit signed hex to signed int
        temp = (int(self.data, 16) - 65536) / 100 if int(self.data, 16) > 32767 else (int(self.data, 16)) / 100
        return temp

    def parse_pressure(self):
        # -1 bar to return mbarg
        return int(self.data, 16) - 1000

    def parse_power(self):
        return int(self.data, 16)

    def parse_status(self):
        bits = format(int(self.data, 16), "0>16b")
        return ChillerStatus(bits)

    def parse_fill_level(self):
        value = int(self.data, 16)
        if value == 0:
            return None
        value -= 1
        value /= 10
        return value

    def parse_boolean(self):
        return int(self.data, 16) == 1


class Huber:
    """
    Control class for Huber chillers.
    """
    def __init__(self, aio: aioserial.AioSerial):
        self._serial = aio

    async def get_temperature_setpoint(self) -> float:
        """ Returns the set point used by temperature controller. Internal if not probe, otherwise process temp. """
        reply = await self.send_command_and_read_reply("{M00****")
        return PBCommand(reply).parse_temperature()

    async def set_temperature_setpoint(self, temp) -> float:
        """ Set the set point used by temperature controller. Internal if not probe, otherwise process temp. """
        reply = await self.send_command_and_read_reply("{M00"+self.temp_to_string(temp))
        return PBCommand(reply).parse_temperature()

    async def internal_temperature(self) -> float:
        """ Returns internal temp (bath temperature). """
        reply = await self.send_command_and_read_reply("{M01****")
        return PBCommand(reply).parse_temperature()

    async def return_temperature(self) -> float:
        """ Returns the temp of the thermal fluid flowing back to the device. """
        reply = await self.send_command_and_read_reply("{M02****")
        return PBCommand(reply).parse_temperature()

    async def pump_pressure(self) -> float:
        """ Return pump pressure in mbarg """
        reply = await self.send_command_and_read_reply("{M03****")
        return PBCommand(reply).parse_pressure()

    async def current_power(self) -> float:
        """ Returns the current power in Watts (negative for cooling, positive for heating). """
        reply = await self.send_command_and_read_reply("{M04****")
        return PBCommand(reply).parse_power()
    
    async def status(self) -> ChillerStatus:
        """ Returns the current power in Watts (negative for cooling, positive for heating). """
        reply = await self.send_command_and_read_reply("{M0A****")
        return PBCommand(reply).parse_status()

    async def fill_level(self) -> float:
        """ Returns the current fill level. None if unavailable """
        reply = await self.send_command_and_read_reply("{M0F****")
        return PBCommand(reply).parse_fill_level()

    async def send_command_and_read_reply(self, command: str) -> str:
        # If newline is forgotten add it :D
        if len(command) == 8:
            command += "\r\n"
        pb_command = PBCommand(command)
        await self._serial.write_async(pb_command.to_chiller())
        reply = await self._serial.readline_async()
        return reply.decode("ascii")

    async def get_temperature_control(self) -> bool:
        """ Returns whether temperature control is active or not. """
        reply = await self.send_command_and_read_reply("{M14****")
        return PBCommand(reply).parse_boolean()

    async def set_temperature_control(self, value: bool):
        if value:
            await self.send_command_and_read_reply("{M140001")
        else:
            await self.send_command_and_read_reply("{M140000")

    async def get_circulation(self) -> bool:
        """ Returns whether temperature control is active or not. """
        reply = await self.send_command_and_read_reply("{M16****")
        return PBCommand(reply).parse_boolean()

    async def set_circulation(self, value: bool):
        if value:
            await self.send_command_and_read_reply("{M160001")
        else:
            await self.send_command_and_read_reply("{M160000")



    @staticmethod
    def temp_to_string(temp: float) -> str:
        assert -151 <= temp <= 327
        # Hexadecimal two's complement to represent numbers
        return f"{int(temp * 100) & 65535:04X}"


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    async def main(chiller: Huber):
        set = await chiller.get_temperature_setpoint()
        cur = await chiller.internal_temperature()
        ret = await  chiller.return_temperature()
        pp = await chiller.pump_pressure()
        pow = await chiller.current_power()
        fl = await chiller.fill_level()
        print(f"I have set{set} and cur {cur} return temp is {ret} pump pressure {pp} mbar pow {pow} leve {fl}")
        status = await chiller.status()
        print(status)
        await chiller.set_temperature_control(True)
        await chiller.set_circulation(True)
        status = await chiller.status()
        print(status)
        await chiller.set_temperature_setpoint(15)
        time.sleep(2)
        await chiller.set_temperature_control(False)
        await chiller.set_circulation(False)
        status = await chiller.status()
        print(status)


    chiller = Huber(aioserial.AioSerial(port='COM1'))
    coro = main(chiller)
    asyncio.run(coro)
