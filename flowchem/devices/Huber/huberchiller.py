"""
Driver for Huber chillers.
"""
import logging
from typing import List, Iterable, Dict

import aioserial
import asyncio
from dataclasses import dataclass


@dataclass
class PBCommand:
    """ Class representing a PBCommand """

    command: str

    def to_chiller(self) -> bytes:
        """ Validate and encode to bytes array to be transmitted. """
        self.validate()
        return self.command.encode("ascii")

    def validate(self):
        """ Check command structure to be compliant with PB format """
        if len(self.command) == 8:
            self.command += "\r\n"
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
    def data(self) -> str:
        """ Data portion of PBCommand. """
        return self.command[4:8]

    def parse_temperature(self):
        """ Parse a device temp from hex string to celsius float [two's complement 16 bit signed hex, see manual] """
        temp = (int(self.data, 16) - 65536) / 100 if int(self.data, 16) > 32767 else (int(self.data, 16)) / 100
        return temp

    def parse_integer(self):
        """ Parse a device reply from hexadecimal string to to base 10 integers. """
        return int(self.data, 16)

    def parse_bits(self) -> List[bool]:
        """" Parse a device reply from hexadecimal string to 16 constituting bits. """
        bits = f"{int(self.data, 16):016b}"
        return list(map(bool, bits))

    def parse_boolean(self):
        """" Parse a device reply from hexadecimal string (0x0000 or 0x0001) to boolean. """
        return self.parse_integer() == 1

    def parse_status1(self) -> Dict[str, bool]:
        """ Parse response to status1 command and returns dict """
        bits = self.parse_bits()
        return dict(
            temp_ctl_is_process=bits[0],
            circulation_active=bits[1],
            refrigerator_on=bits[2],
            temp_is_process=bits[3],
            circulating_pump=bits[4],
            cooling_power_available=bits[5],
            tkeylock=bits[6],
            is_pid_auto=bits[7],
            error=bits[8],
            warning=bits[9],
            int_temp_mode=bits[10],
            ext_temp_mode=bits[11],
            dv_e_grade=bits[12],
            power_failure=bits[13],
            freeze_protection=bits[14],
        )


class HuberChiller:
    """
    Control class for Huber chillers.
    """
    def __init__(self, aio: aioserial.AioSerial):
        self._serial = aio
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_config(cls, config: dict):
        """
        Create instance from config dict. Used by server to initialize obj from config.

        Only required parameter is 'port'. Optional 'loop' + others (see AioSerial())
        """
        serial_object = aioserial.AioSerial(**config)
        return cls(serial_object)

    async def send_command_and_read_reply(self, command: str) -> str:
        """ Sends a command to the chiller and reads the reply.

        :param command: string to be transmitted
        :return: reply received
        """
        # Send command. Using PBCommand ensure command validation, see PBCommand.to_chiller()
        pb_command = PBCommand(command)
        await self._serial.write_async(pb_command.to_chiller())
        self.logger.debug(f"Command {command[0:8]} sent to chiller!")

        # Receive reply and return it after decoding
        reply = await self._serial.readline_async()
        self.logger.debug(f"Reply {reply[0:8].decode('ascii')} received")
        return reply.decode("ascii")

    async def get_temperature_setpoint(self) -> float:
        """ Returns the set point used by temperature controller. Internal if not probe, otherwise process temp. """
        reply = await self.send_command_and_read_reply("{M00****")
        return PBCommand(reply).parse_temperature()

    async def set_temperature_setpoint(self, temp: float):
        """ Set the set point used by temperature controller. Internal if not probe, otherwise process temp. """
        min_t = await self.min_setpoint()
        max_t = await self.max_setpoint()
        assert min_t <= temp <= max_t
        await self.send_command_and_read_reply("{M00"+self.temp_to_string(temp))

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
        return PBCommand(reply).parse_integer() - 1000

    async def current_power(self) -> float:
        """ Returns the current power in Watts (negative for cooling, positive for heating). """
        reply = await self.send_command_and_read_reply("{M04****")
        return PBCommand(reply).parse_integer()

    async def status(self) -> Dict[str, bool]:
        """ Returns the current power in Watts (negative for cooling, positive for heating). """
        reply = await self.send_command_and_read_reply("{M0A****")
        return PBCommand(reply).parse_status1()

    async def get_temperature_control(self) -> bool:
        """ Returns whether temperature control is active or not. """
        reply = await self.send_command_and_read_reply("{M14****")
        return PBCommand(reply).parse_boolean()

    async def start_temperature_control(self):
        """ Starts temperature control, i.e. start operation. """
        await self.send_command_and_read_reply("{M140001")

    async def stop_temperature_control(self):
        """ Stops temperature control, i.e. stop operation. """
        await self.send_command_and_read_reply("{M140000")

    async def get_circulation(self) -> bool:
        """ Returns whether temperature control is active or not. """
        reply = await self.send_command_and_read_reply("{M16****")
        return PBCommand(reply).parse_boolean()

    async def start_circulation(self):
        """ Starts circulation pump. """
        await self.send_command_and_read_reply("{M160001")

    async def stop_circulation(self):
        """ Stops circulation pump. """
        await self.send_command_and_read_reply("{M160000")

    async def pump_speed(self) -> int:
        """ Returns current circulation pump speed (in rpm). """
        rpm = await self.send_command_and_read_reply("{M26****")
        return PBCommand(rpm).parse_integer()

    async def pump_speed_setpoint(self) -> int:
        """ Returns the set point of the circulation pump speed (in rpm). """
        rpm = await self.send_command_and_read_reply("{M48****")
        return PBCommand(rpm).parse_integer()

    async def set_pump_speed(self, rpm: int):
        """ Set the pump speed, in rpm. See device display for range. """
        await self.send_command_and_read_reply("{M48"+self.int_to_string(rpm))

    async def cooling_water_temp(self) -> float:
        """ Returns the cooling water inlet temperature (in Celsius). """
        temp = await self.send_command_and_read_reply("{M2C****")
        return PBCommand(temp).parse_temperature()

    async def cooling_water_pressure(self) -> float:
        """ Returns the cooling water inlet pressure (in mbar). """
        pressure = await self.send_command_and_read_reply("{M2D****")
        return PBCommand(pressure).parse_integer()

    async def min_setpoint(self) -> float:
        """ Returns the minimum accepted value for the temperature setpoint (in Celsius). """
        temp_reply = await self.send_command_and_read_reply("{M30****")
        return PBCommand(temp_reply).parse_temperature()

    async def max_setpoint(self) -> float:
        """ Returns the maximum accepted value for the temperature setpoint (in Celsius). """
        temp_reply = await self.send_command_and_read_reply("{M31****")
        return PBCommand(temp_reply).parse_temperature()

    @staticmethod
    def temp_to_string(temp: float) -> str:
        """ From temperature to string for command. f^-1 of PCommand.parse_temperature. """
        assert -151 <= temp <= 327
        # Hexadecimal two's complement
        return f"{int(temp * 100) & 65535:04X}"

    @staticmethod
    def int_to_string(number: int) -> str:
        """ From temperature to string for command. f^-1 of PCommand.parse_integer. """
        return f"{number:04X}"

    def get_router(self):
        """ Creates an APIRouter for the instance. """
        # Local import to allow direct use of HuberChiller w/o fastapi installed
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/temperature/setpoint", self.get_temperature_setpoint, methods=["GET"])
        router.add_api_route("/temperature/setpoint/min", self.min_setpoint, methods=["GET"])
        router.add_api_route("/temperature/setpoint/max", self.max_setpoint, methods=["GET"])
        router.add_api_route("/temperature/setpoint", self.set_temperature_setpoint, methods=["PUT"])
        router.add_api_route("/temperature/internal", self.internal_temperature, methods=["GET"])
        router.add_api_route("/temperature/return", self.return_temperature, methods=["GET"])
        router.add_api_route("/power-exchanged", self.current_power, methods=["GET"])
        router.add_api_route("/status", self.status, methods=["GET"])
        router.add_api_route("/pump/speed", self.pump_speed, methods=["GET"])
        router.add_api_route("/temperature-control", self.get_temperature_control, methods=["GET"])
        router.add_api_route("/temperature-control/start", self.start_temperature_control, methods=["GET"])
        router.add_api_route("/temperature-control/stop", self.stop_temperature_control, methods=["GET"])
        router.add_api_route("/pump/circulation", self.get_circulation, methods=["GET"])
        router.add_api_route("/pump/circulation/start", self.start_circulation, methods=["GET"])
        router.add_api_route("/pump/circulation/stop", self.stop_circulation, methods=["GET"])
        router.add_api_route("/pump/pressure", self.pump_pressure, methods=["GET"])
        router.add_api_route("/pump/speed", self.pump_speed, methods=["GET"])
        router.add_api_route("/pump/speed/setpoint", self.pump_speed_setpoint, methods=["GET"])
        router.add_api_route("/pump/speed/setpoint", self.set_pump_speed, methods=["PUT"])
        router.add_api_route("/cooling-water/temperature", self.cooling_water_temp, methods=["GET"])
        router.add_api_route("/cooling-water/pressure", self.cooling_water_pressure, methods=["GET"])

if __name__ == '__main__':
    chiller = HuberChiller(aioserial.AioSerial(port='COM1'))
    status = asyncio.run(chiller.status())
    print(status)
