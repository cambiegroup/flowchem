"""
Driver for Huber chillers.
"""
import asyncio
import logging
import warnings
from dataclasses import dataclass
from typing import List, Dict, Optional

import aioserial
from aioserial import SerialException

from flowchem.constants import InvalidConfiguration


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
        return [bool(int(x)) for x in bits]

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

    def parse_status2(self) -> Dict[str, bool]:
        """ Parse response to status2 command and returns dict. See manufacturer docs for more info """
        bits = self.parse_bits()
        return dict(
            controller_is_external=bits[0],
            drip_tray_full=bits[5],
            venting_active=bits[7],
            venting_successful=bits[8],
            venting_monitored=bits[9],
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
        try:
            serial_object = aioserial.AioSerial(**config)
        except SerialException as e:
            raise InvalidConfiguration(f"Cannot connect to the HuberChiller on the port <{config.get('port')}>") from e

        return cls(serial_object)

    async def send_command_and_read_reply(self, command: str) -> str:
        """ Sends a command to the chiller and reads the reply.

        :param command: string to be transmitted
        :return: reply received
        """
        # Send command. Using PBCommand ensure command validation, see PBCommand.to_chiller()
        pb_command = PBCommand(command.upper())
        await self._serial.write_async(pb_command.to_chiller())
        self.logger.debug(f"Command {command[0:8]} sent to chiller!")

        # Receive reply and return it after decoding
        try:
            reply = await asyncio.wait_for(self._serial.readline_async(), 1)
        except asyncio.TimeoutError:
            warnings.warn("No reply received. Likely the command is not supported by the hardware!")
            self.logger.error(f"No reply received")
            return command.replace("M", "S").replace("****", "0000")  # Fake reply to keep going

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

        if temp > max_t:
            temp = max_t
            warnings.warn(f"Temperature requested {temp} is out of range [{min_t} - {max_t}] for HuberChiller {self}!"
                          f"Setting to {max_t} instead.")
        if temp < min_t:
            temp = min_t
            warnings.warn(f"Temperature requested {temp} is out of range [{min_t} - {max_t}] for HuberChiller {self}!"
                          f"Setting to {min_t} instead.")

        await self.send_command_and_read_reply("{M00"+self.temp_to_string(temp))

    async def internal_temperature(self) -> float:
        """ Returns internal temp (bath temperature). """
        reply = await self.send_command_and_read_reply("{M01****")
        return PBCommand(reply).parse_temperature()

    async def process_temperature(self) -> Optional[float]:
        """ Returns the current process temperature. If not T probe, the device returns -151, here parsed as None. """
        reply = await self.send_command_and_read_reply("{M3A****")
        if temp := PBCommand(reply).parse_temperature() == -151:
            return None
        else:
            return temp

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
        """ Returns the info contained in vstatus1 as dict. """
        reply = await self.send_command_and_read_reply("{M0A****")
        return PBCommand(reply).parse_status1()

    async def status2(self) -> Dict[str, bool]:
        """ Returns the info contained in vstatus2 as dict. """
        reply = await self.send_command_and_read_reply("{M3C****")
        return PBCommand(reply).parse_status2()

    async def is_temperature_control_active(self) -> bool:
        """ Returns whether temperature control is active or not. """
        reply = await self.send_command_and_read_reply("{M14****")
        return PBCommand(reply).parse_boolean()

    async def start_temperature_control(self):
        """ Starts temperature control, i.e. start operation. """
        await self.send_command_and_read_reply("{M140001")

    async def stop_temperature_control(self):
        """ Stops temperature control, i.e. stop operation. """
        await self.send_command_and_read_reply("{M140000")

    async def is_circulation_active(self) -> bool:
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
        reply = await self.send_command_and_read_reply("{M26****")
        return PBCommand(reply).parse_integer()

    async def pump_speed_setpoint(self) -> int:
        """ Returns the set point of the circulation pump speed (in rpm). """
        reply = await self.send_command_and_read_reply("{M48****")
        return PBCommand(reply).parse_integer()

    async def set_pump_speed(self, rpm: int):
        """ Set the pump speed, in rpm. See device display for range. """
        await self.send_command_and_read_reply("{M48"+self.int_to_string(rpm))

    async def cooling_water_temp(self) -> Optional[float]:
        """ Returns the cooling water inlet temperature (in Celsius). """
        reply = await self.send_command_and_read_reply("{M2C****")
        if temp := PBCommand(reply).parse_temperature() == -151:
            return None
        else:
            return temp

    async def cooling_water_pressure(self) -> Optional[float]:
        """ Returns the cooling water inlet pressure (in mbar). """
        reply = await self.send_command_and_read_reply("{M2D****")
        if pressure := PBCommand(reply).parse_integer() == 64536:
            return None
        else:
            return pressure

    async def cooling_water_temp_outflow(self) -> Optional[float]:
        """ Returns the cooling water outlet temperature (in Celsius). """
        reply = await self.send_command_and_read_reply("{M4C****")
        if temp := PBCommand(reply).parse_temperature() == -151:
            return None
        else:
            return temp

    async def min_setpoint(self) -> float:
        """ Returns the minimum accepted value for the temperature setpoint (in Celsius). """
        reply = await self.send_command_and_read_reply("{M30****")
        return PBCommand(reply).parse_temperature()

    async def max_setpoint(self) -> float:
        """ Returns the maximum accepted value for the temperature setpoint (in Celsius). """
        reply = await self.send_command_and_read_reply("{M31****")
        return PBCommand(reply).parse_temperature()

    async def alarm_max_internal_temp(self) -> float:
        """ Returns the max internal temp before the alarm is triggered and a fault generated. """
        reply = await self.send_command_and_read_reply("{M51****")
        return PBCommand(reply).parse_temperature()

    async def set_alarm_max_internal_temp(self, temp: float):
        """ Sets the max internal temp before the alarm is triggered and a fault generated. """
        await self.send_command_and_read_reply("{M51" + self.temp_to_string(temp))

    async def alarm_min_internal_temp(self) -> float:
        """ Returns the min internal temp before the alarm is triggered and a fault generated. """
        reply = await self.send_command_and_read_reply("{M52****")
        return PBCommand(reply).parse_temperature()

    async def set_alarm_min_internal_temp(self, temp: float):
        """ Sets the min internal temp before the alarm is triggered and a fault generated. """
        await self.send_command_and_read_reply("{M52" + self.temp_to_string(temp))

    async def alarm_max_process_temp(self) -> float:
        """ Returns the max process temp before the alarm is triggered and a fault generated. """
        reply = await self.send_command_and_read_reply("{M53****")
        return PBCommand(reply).parse_temperature()

    async def set_alarm_max_process_temp(self, temp: float):
        """ Sets the max process temp before the alarm is triggered and a fault generated. """
        await self.send_command_and_read_reply("{M53" + self.temp_to_string(temp))

    async def alarm_min_process_temp(self) -> float:
        """ Returns the min process temp before the alarm is triggered and a fault generated. """
        reply = await self.send_command_and_read_reply("{M54****")
        return PBCommand(reply).parse_temperature()

    async def set_alarm_min_process_temp(self, temp: float):
        """ Sets the min process temp before the alarm is triggered and a fault generated. """
        await self.send_command_and_read_reply("{M54" + self.temp_to_string(temp))

    async def set_ramp_duration(self, time: int):
        """ Sets the duration (in seconds) of a ramp to the temperature set by a later call to ramp_to_temperature. """
        await self.send_command_and_read_reply("{M59" + self.int_to_string(time))

    async def ramp_to_temperature(self, temperature: float):
        """ Sets the duration (in seconds) of a ramp to the temperature set by a later call to start_ramp(). """
        await self.send_command_and_read_reply("{M5A" + self.temp_to_string(temperature))

    async def is_venting(self) -> bool:
        """ Whether the chiller is venting or not. """
        reply = await self.send_command_and_read_reply("{M6F****")
        return PBCommand(reply).parse_boolean()

    async def start_venting(self):
        """ Starts venting. ONLY USE DURING SETUP! READ THE MANUAL!"""
        await self.send_command_and_read_reply("{M6F0001")

    async def stop_venting(self):
        """ Stops venting. """
        await self.send_command_and_read_reply("{M6F0000")

    async def is_draining(self) -> bool:
        """ Whether the chiller is venting or not.  """
        reply = await self.send_command_and_read_reply("{M70****")
        return PBCommand(reply).parse_boolean()

    async def start_draining(self):
        """ Starts venting. ONLY USE DURING SHUT DOWN! READ THE MANUAL!"""
        await self.send_command_and_read_reply("{M700001")

    async def stop_draining(self):
        """ Stops venting. """
        await self.send_command_and_read_reply("{M700000")

    async def serial_number(self) -> int:
        """ GGet serial number. """
        s1 = await self.send_command_and_read_reply("{M1B****")
        s2 = await self.send_command_and_read_reply("{M1C****")
        pb1, pb2 = PBCommand(s1), PBCommand(s2)
        return int(pb1.data+pb2.data, 16)

    async def wait_for_temperature_simple(self) -> None:
        """ Returns as soon as the target temperature range has been reached, or timeout. """
        raise NotImplementedError

    async def wait_for_temperature_stable(self) -> None:
        """ Returns when the target temperature range has been maintained for X seconds, or timeout. """
        raise NotImplementedError

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
        """ Creates an APIRouter for this HuberChiller instance. """
        # Local import to allow direct use of HuberChiller w/o fastapi installed
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/temperature/set-point", self.get_temperature_setpoint, methods=["GET"])
        router.add_api_route("/temperature/set-point", self.set_temperature_setpoint, methods=["PUT"])
        router.add_api_route("/temperature/set-point/min", self.min_setpoint, methods=["GET"])
        router.add_api_route("/temperature/set-point/max", self.max_setpoint, methods=["GET"])
        router.add_api_route("/temperature/process", self.process_temperature, methods=["GET"])
        router.add_api_route("/temperature/internal", self.internal_temperature, methods=["GET"])
        router.add_api_route("/temperature/return", self.return_temperature, methods=["GET"])
        router.add_api_route("/power-exchanged", self.current_power, methods=["GET"])
        router.add_api_route("/status", self.status, methods=["GET"])
        router.add_api_route("/status2", self.status2, methods=["GET"])
        router.add_api_route("/pump/speed", self.pump_speed, methods=["GET"])
        router.add_api_route("/temperature-control", self.is_temperature_control_active, methods=["GET"])
        router.add_api_route("/temperature-control/start", self.start_temperature_control, methods=["GET"])
        router.add_api_route("/temperature-control/stop", self.stop_temperature_control, methods=["GET"])
        router.add_api_route("/pump/circulation", self.is_circulation_active, methods=["GET"])
        router.add_api_route("/pump/circulation/start", self.start_circulation, methods=["GET"])
        router.add_api_route("/pump/circulation/stop", self.stop_circulation, methods=["GET"])
        router.add_api_route("/pump/pressure", self.pump_pressure, methods=["GET"])
        router.add_api_route("/pump/speed", self.pump_speed, methods=["GET"])
        router.add_api_route("/pump/speed/set-point", self.pump_speed_setpoint, methods=["GET"])
        router.add_api_route("/pump/speed/set-point", self.set_pump_speed, methods=["PUT"])
        router.add_api_route("/cooling-water/temperature-inlet", self.cooling_water_temp, methods=["GET"])
        router.add_api_route("/cooling-water/temperature-outlet", self.cooling_water_temp_outflow, methods=["GET"])
        router.add_api_route("/cooling-water/pressure", self.cooling_water_pressure, methods=["GET"])
        router.add_api_route("/alarm/process/min-temp", self.alarm_min_process_temp, methods=["GET"])
        router.add_api_route("/alarm/process/max-temp", self.alarm_max_process_temp, methods=["GET"])
        router.add_api_route("/alarm/process/min-temp", self.set_alarm_min_process_temp, methods=["PUT"])
        router.add_api_route("/alarm/process/max-temp", self.set_alarm_min_process_temp, methods=["PUT"])
        router.add_api_route("/alarm/internal/min-temp", self.alarm_min_internal_temp, methods=["GET"])
        router.add_api_route("/alarm/internal/max-temp", self.alarm_max_internal_temp, methods=["GET"])
        router.add_api_route("/alarm/internal/min-temp", self.set_alarm_min_internal_temp, methods=["PUT"])
        router.add_api_route("/alarm/internal/max-temp", self.set_alarm_min_internal_temp, methods=["PUT"])
        router.add_api_route("/venting/is_venting", self.is_venting, methods=["GET"])
        router.add_api_route("/venting/start", self.start_venting, methods=["GET"])
        router.add_api_route("/venting/stop", self.stop_venting, methods=["GET"])
        router.add_api_route("/draining/is_venting", self.is_draining, methods=["GET"])
        router.add_api_route("/draining/start", self.start_draining, methods=["GET"])
        router.add_api_route("/draining/stop", self.stop_draining, methods=["GET"])
        router.add_api_route("/serial_number", self.serial_number, methods=["GET"])

        return router


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    chiller = HuberChiller(aioserial.AioSerial(port='COM8'))
    status = asyncio.run(chiller.status())
    print(status)