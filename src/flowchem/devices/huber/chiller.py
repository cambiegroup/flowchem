"""Huber chiller control driver."""
import asyncio
import warnings
from dataclasses import dataclass

import aioserial
import pint
from loguru import logger

from flowchem import ureg
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.exceptions import InvalidConfiguration
from flowchem.people import *


class HuberChiller(FlowchemDevice):
    """Control class for Huber chillers."""

    @dataclass
    class PBCommand:
        """Class representing a PBCommand."""

        command: str

        def to_chiller(self) -> bytes:
            """Validate and encode to bytes array to be transmitted."""
            self.validate()
            return self.command.encode("ascii")

        def validate(self):
            """Check command structure to be compliant with PB format."""
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
            assert (
                self.command[4:8] == "****" or 0 <= int(self.command[4:8], 16) <= 65536
            )
            # EOL
            assert self.command[8:10] == "\r\n"

        @property
        def data(self) -> str:
            """Data portion of PBCommand."""
            return self.command[4:8]

        def parse_temperature(self) -> float | None:
            """Parse a device temp from hex string to celsius float."""
            # self.data is the two's complement 16-bit signed hex, see manual
            temp = (
                (int(self.data, 16) - 65536) / 100
                if int(self.data, 16) > 32767
                else (int(self.data, 16)) / 100
            )
            # -151 used for invalid temperatures
            if temp == -151:
                return None
            return temp

        def parse_integer(self) -> int:
            """Parse a device reply from hexadecimal string to base 10 integers."""
            return int(self.data, 16)

        def parse_rpm(self) -> str:
            """Parse a device reply from hexadecimal string to rpm."""
            return str(ureg(f"{self.parse_integer()} rpm"))

        def parse_bits(self) -> list[bool]:
            """Parse a device reply from hexadecimal string to 16 constituting bits."""
            bits = f"{int(self.data, 16):016b}"
            return [bool(int(x)) for x in bits]

        def parse_boolean(self):
            """Parse a device reply from hexadecimal string (0x0000 or 0x0001) to boolean."""
            return self.parse_integer() == 1

        def parse_status1(self) -> dict[str, bool]:
            """Parse response to status1 command and returns dict."""
            bits = self.parse_bits()
            return {
                "temp_ctl_is_process": bits[0],
                "circulation_active": bits[1],
                "refrigerator_on": bits[2],
                "temp_is_process": bits[3],
                "circulating_pump": bits[4],
                "cooling_power_available": bits[5],
                "tkeylock": bits[6],
                "is_pid_auto": bits[7],
                "error": bits[8],
                "warning": bits[9],
                "int_temp_mode": bits[10],
                "ext_temp_mode": bits[11],
                "dv_e_grade": bits[12],
                "power_failure": bits[13],
                "freeze_protection": bits[14],
            }

        def parse_status2(self) -> dict[str, bool]:
            """Parse response to status2 command and returns dict. See manufacturer docs for more info"""
            bits = self.parse_bits()
            return {
                "controller_is_external": bits[0],
                "drip_tray_full": bits[5],
                "venting_active": bits[7],
                "venting_successful": bits[8],
                "venting_monitored": bits[9],
            }

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio: aioserial.AioSerial, name=None):
        super().__init__(name)
        self._serial = aio
        self.device_sn: int = None  # type: ignore

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs):
        """
        Create instance from config dict. Used by server to initialize obj from config.

        Only required parameter is 'port'. Optional 'loop' + others (see AioSerial())
        """
        # Merge default settings, including serial, with provided ones.
        configuration = HuberChiller.DEFAULT_CONFIG | serial_kwargs

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except (OSError, aioserial.SerialException) as serial_exception:
            raise InvalidConfiguration(
                f"Cannot connect to the HuberChiller on the port <{port}>"
            ) from serial_exception

        return cls(serial_object, name)

    async def initialize(self):
        """Ensure the connection w/ device is working."""
        serial_num = await self.serial_number()
        if serial_num == 0:
            raise InvalidConfiguration("No reply received from Huber Chiller!")
        self.device_sn = serial_num
        logger.debug(f"Connected with Huber Chiller S/N {serial_num}")

    def metadata(self) -> DeviceInfo:
        """Return hw device metadata."""
        return DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="Huber",
            model="generic chiller",
            serial_number=self.device_sn,
        )

    async def _send_command_and_read_reply(self, command: str) -> str:
        """Send a command to the chiller and read the reply.

        Args:
            command (str): string to be transmitted

        Returns:
            str: reply received
        """
        # Send command. Using PBCommand ensure command validation, see PBCommand.to_chiller()
        pb_command = self.PBCommand(command.upper())
        await self._serial.write_async(pb_command.to_chiller())
        logger.debug(f"Command {command[0:8]} sent to chiller!")

        # Receive reply and return it after decoding
        try:
            reply = await asyncio.wait_for(self._serial.readline_async(), 1)
        except asyncio.TimeoutError:
            warnings.warn(
                "No reply received. Likely the command is not supported by the hardware!"
            )
            logger.error("No reply received")
            return command.replace("M", "S").replace(
                "****", "0000"
            )  # Fake reply to keep going

        logger.debug(f"Reply received: {reply}")
        return reply.decode("ascii")

    async def get_temperature(self) -> float:
        """Get temperature. Process preferred, otherwise internal."""
        if process_t := await self.process_temperature():
            return process_t
        return await self.internal_temperature()  # type: ignore

    async def get_temperature_setpoint(self) -> float | None:
        """Return the set point used by temperature controller. Internal if not probe, otherwise process temp."""
        reply = await self._send_command_and_read_reply("{M00****")
        return self.PBCommand(reply).parse_temperature()

    async def set_temperature(self, temp: str):
        """Set the set point used by temperature controller. Internal if not probe, otherwise process temp."""
        t_limits = await self.temperature_limits()
        min_t = ureg(f"{t_limits['min']} degC")
        max_t = ureg(f"{t_limits['max']} degC")
        set_t = ureg(temp)

        if set_t > max_t:
            set_t = max_t
            warnings.warn(
                f"Temperature requested {set_t} is out of range [{min_t} - {max_t}] for HuberChiller {self}!"
                f"Setting to {max_t} instead."
            )
        if set_t < min_t:
            set_t = min_t
            warnings.warn(
                f"Temperature requested {set_t} is out of range [{min_t} - {max_t}] for HuberChiller {self}!"
                f"Setting to {min_t} instead."
            )

        await self._send_command_and_read_reply("{M00" + self._temp_to_string(set_t))

    async def target_reached(self):
        """Trivially implemented as delta(currentT-setT) < 1°C."""
        current_t = await self.get_temperature()
        set_t = await self.get_temperature_setpoint()
        if set_t:
            return abs(current_t - set_t) < 1
        return False

    async def internal_temperature(self) -> float | None:
        """Return internal temp (bath temperature)."""
        reply = await self._send_command_and_read_reply("{M01****")
        return self.PBCommand(reply).parse_temperature()

    async def process_temperature(self) -> float | None:
        """Return the current process temperature. If not T probe, the temperature is None."""
        reply = await self._send_command_and_read_reply("{M3A****")
        return self.PBCommand(reply).parse_temperature()

    async def return_temperature(self) -> float | None:
        """Return the temp of the thermal fluid flowing back to the device."""
        reply = await self._send_command_and_read_reply("{M02****")
        return self.PBCommand(reply).parse_temperature()

    async def pump_pressure(self) -> str:
        """Return the pump pressure in mbar (note that you probably want barg, i.e. to remove 1 bar)."""
        reply = await self._send_command_and_read_reply("{M03****")
        pressure = self.PBCommand(reply).parse_integer()
        return str(ureg(f"{pressure} mbar"))

    async def current_power(self) -> str:
        """Return the current power in Watts (negative for cooling, positive for heating)."""
        reply = await self._send_command_and_read_reply("{M04****")
        power = self.PBCommand(reply).parse_integer()
        return str(ureg(f"{power} watt"))

    async def status(self) -> dict[str, bool]:
        """Return the info contained in `vstatus1` as dict."""
        reply = await self._send_command_and_read_reply("{M0A****")
        return self.PBCommand(reply).parse_status1()

    async def status2(self) -> dict[str, bool]:
        """Return the info contained in `vstatus2` as dict."""
        reply = await self._send_command_and_read_reply("{M3C****")
        return self.PBCommand(reply).parse_status2()

    async def is_temperature_control_active(self) -> bool:
        """Return whether temperature control is active or not."""
        reply = await self._send_command_and_read_reply("{M14****")
        return self.PBCommand(reply).parse_boolean()

    async def power_on(self):
        """Start temperature control, i.e. start operation."""
        await self._send_command_and_read_reply("{M140001")

    async def power_off(self):
        """Stop temperature control, i.e. stop operation."""
        await self._send_command_and_read_reply("{M140000")

    async def is_circulation_active(self) -> bool:
        """Return whether temperature control is active or not."""
        reply = await self._send_command_and_read_reply("{M16****")
        return self.PBCommand(reply).parse_boolean()

    async def start_circulation(self):
        """Start circulation pump."""
        await self._send_command_and_read_reply("{M160001")

    async def stop_circulation(self):
        """Stop circulation pump."""
        await self._send_command_and_read_reply("{M160000")

    async def pump_speed(self) -> str:
        """Return current circulation pump speed (in rpm)."""
        reply = await self._send_command_and_read_reply("{M26****")
        return self.PBCommand(reply).parse_rpm()

    async def pump_speed_setpoint(self) -> str:
        """Return the set point of the circulation pump speed (in rpm)."""
        reply = await self._send_command_and_read_reply("{M48****")
        return self.PBCommand(reply).parse_rpm()

    async def set_pump_speed(self, rpm: str):
        """Set the pump speed, in rpm. See device display for range."""
        parsed_rpm = ureg(rpm)
        await self._send_command_and_read_reply(
            "{M48" + self._int_to_string(parsed_rpm.m_as("rpm"))
        )

    async def cooling_water_temp(self) -> float | None:
        """Return the cooling water inlet temperature (in Celsius)."""
        reply = await self._send_command_and_read_reply("{M2C****")
        return self.PBCommand(reply).parse_temperature()

    async def cooling_water_pressure(self) -> float | None:
        """Return the cooling water inlet pressure (in mbar)."""
        reply = await self._send_command_and_read_reply("{M2D****")
        if pressure := self.PBCommand(reply).parse_integer() == 64536:
            return None
        return pressure

    async def cooling_water_temp_outflow(self) -> float | None:
        """Return the cooling water outlet temperature (in Celsius)."""
        reply = await self._send_command_and_read_reply("{M4C****")
        return self.PBCommand(reply).parse_temperature()

    async def temperature_limits(self) -> dict[str, float]:
        """Return minimum/maximum accepted value for the temperature setpoint (in Celsius)."""
        min_reply = await self._send_command_and_read_reply("{M30****")
        min_t = self.PBCommand(min_reply).parse_temperature()
        max_reply = await self._send_command_and_read_reply("{M31****")
        max_t = self.PBCommand(max_reply).parse_temperature()
        return {
            "min": min_t,  # type: ignore
            "max": max_t,  # type: ignore
        }

    async def alarm_max_internal_temp(self) -> float | None:
        """Return the max internal temp before the alarm is triggered and a fault generated."""
        reply = await self._send_command_and_read_reply("{M51****")
        return self.PBCommand(reply).parse_temperature()

    async def set_alarm_max_internal_temp(self, set_temp: str):
        """Set the max internal temp before the alarm is triggered and a fault generated."""
        temp = ureg(set_temp)
        await self._send_command_and_read_reply("{M51" + self._temp_to_string(temp))

    async def alarm_min_internal_temp(self) -> float | None:
        """Return the min internal temp before the alarm is triggered and a fault generated."""
        reply = await self._send_command_and_read_reply("{M52****")
        return self.PBCommand(reply).parse_temperature()

    async def set_alarm_min_internal_temp(self, set_temp: str):
        """Set the min internal temp before the alarm is triggered and a fault generated."""
        temp = ureg(set_temp)
        await self._send_command_and_read_reply("{M52" + self._temp_to_string(temp))

    async def alarm_max_process_temp(self) -> float | None:
        """Return the max process temp before the alarm is triggered and a fault generated."""
        reply = await self._send_command_and_read_reply("{M53****")
        return self.PBCommand(reply).parse_temperature()

    async def set_alarm_max_process_temp(self, set_temp: str):
        """Set the max process temp before the alarm is triggered and a fault generated."""
        temp = ureg(set_temp)
        await self._send_command_and_read_reply("{M53" + self._temp_to_string(temp))

    async def alarm_min_process_temp(self) -> float | None:
        """Return the min process temp before the alarm is triggered and a fault generated."""
        reply = await self._send_command_and_read_reply("{M54****")
        return self.PBCommand(reply).parse_temperature()

    async def set_alarm_min_process_temp(self, set_temp: str):
        """Set the min process temp before the alarm is triggered and a fault generated."""
        temp = ureg(set_temp)
        await self._send_command_and_read_reply("{M54" + self._temp_to_string(temp))

    async def set_ramp_duration(self, ramp_time: str):
        """Set the duration (in seconds) of a ramp to the temperature set by a later call to ramp_to_temperature."""
        parsed_time = ureg(ramp_time)
        await self._send_command_and_read_reply(
            "{M59" + self._int_to_string(parsed_time.m_as("s"))
        )

    async def ramp_to_temperature(self, temperature: str):
        """Set the duration (in seconds) of a ramp to the temperature set by a later call to start_ramp()."""
        temp = ureg(temperature)
        await self._send_command_and_read_reply("{M5A" + self._temp_to_string(temp))

    async def is_venting(self) -> bool:
        """Whether the chiller is venting or not."""
        reply = await self._send_command_and_read_reply("{M6F****")
        return self.PBCommand(reply).parse_boolean()

    async def start_venting(self):
        """Start venting. ONLY USE DURING SETUP! READ THE MANUAL!"""
        await self._send_command_and_read_reply("{M6F0001")

    async def stop_venting(self):
        """Stop venting."""
        await self._send_command_and_read_reply("{M6F0000")

    async def is_draining(self) -> bool:
        """Whether the chiller is venting or not."""
        reply = await self._send_command_and_read_reply("{M70****")
        return self.PBCommand(reply).parse_boolean()

    async def start_draining(self):
        """Start venting. ONLY USE DURING SHUT DOWN! READ THE MANUAL!"""
        await self._send_command_and_read_reply("{M700001")

    async def stop_draining(self):
        """Stop venting."""
        await self._send_command_and_read_reply("{M700000")

    async def serial_number(self) -> int:
        """Get serial number."""
        serial1 = await self._send_command_and_read_reply("{M1B****")
        serial2 = await self._send_command_and_read_reply("{M1C****")
        pb1, pb2 = self.PBCommand(serial1), self.PBCommand(serial2)
        if pb1.data and pb2.data:
            return int(pb1.data + pb2.data, 16)
        else:
            return 0

    @staticmethod
    def _temp_to_string(temp: pint.Quantity) -> str:
        """From temperature to string for command. f^-1 of PCommand.parse_temperature."""
        min_temp = ureg("-151 °C")
        max_temp = ureg("327 °C")
        if not isinstance(temp, pint.Quantity):
            logger.warning(
                f"Implicit assumption that the temperature provided [{temp}] is in Celsius. Add units pls!"
            )
            temp = ureg(f"{temp} °C")
        assert min_temp <= temp <= max_temp
        # Hexadecimal two's complement
        return f"{int(temp.m_as('°C') * 100) & 65535:04X}"

    @staticmethod
    def _int_to_string(number: int) -> str:
        """From temperature to string for command. f^-1 of PCommand.parse_integer."""
        return f"{number:04X}"

    def get_components(self):
        """Return a TemperatureControl component."""
        # router.add_api_route(
        #     "/temperature/process", self.process_temperature, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/temperature/internal", self.internal_temperature, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/temperature/return", self.return_temperature, methods=["GET"]
        # )
        # router.add_api_route("/power-exchanged", self.current_power, methods=["GET"])
        # router.add_api_route("/status", self.status, methods=["GET"])
        # router.add_api_route("/status2", self.status2, methods=["GET"])
        # router.add_api_route("/pump/speed", self.pump_speed, methods=["GET"])
        # router.add_api_route(
        #     "/temperature-control", self.is_temperature_control_active, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/pump/circulation", self.is_circulation_active, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/pump/circulation/start", self.start_circulation, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/pump/circulation/stop", self.stop_circulation, methods=["GET"]
        # )
        # router.add_api_route("/pump/pressure", self.pump_pressure, methods=["GET"])
        # router.add_api_route("/pump/speed", self.pump_speed, methods=["GET"])
        # router.add_api_route(
        #     "/pump/speed/set-point", self.pump_speed_setpoint, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/pump/speed/set-point", self.set_pump_speed, methods=["PUT"]
        # )
        # router.add_api_route(
        #     "/cooling-water/temperature-inlet", self.cooling_water_temp, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/cooling-water/temperature-outlet",
        #     self.cooling_water_temp_outflow,
        #     methods=["GET"],
        # )
        # router.add_api_route(
        #     "/cooling-water/pressure", self.cooling_water_pressure, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/alarm/process/min-temp", self.alarm_min_process_temp, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/alarm/process/max-temp", self.alarm_max_process_temp, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/alarm/process/min-temp", self.set_alarm_min_process_temp, methods=["PUT"]
        # )
        # router.add_api_route(
        #     "/alarm/process/max-temp", self.set_alarm_min_process_temp, methods=["PUT"]
        # )
        # router.add_api_route(
        #     "/alarm/internal/min-temp", self.alarm_min_internal_temp, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/alarm/internal/max-temp", self.alarm_max_internal_temp, methods=["GET"]
        # )
        # router.add_api_route(
        #     "/alarm/internal/min-temp",
        #     self.set_alarm_min_internal_temp,
        #     methods=["PUT"],
        # )
        # router.add_api_route(
        #     "/alarm/internal/max-temp",
        #     self.set_alarm_min_internal_temp,
        #     methods=["PUT"],
        # )
        # router.add_api_route("/venting/is_venting", self.is_venting, methods=["GET"])
        # router.add_api_route("/venting/start", self.start_venting, methods=["GET"])
        # router.add_api_route("/venting/stop", self.stop_venting, methods=["GET"])
        # router.add_api_route("/draining/is_venting", self.is_draining, methods=["GET"])
        # router.add_api_route("/draining/start", self.start_draining, methods=["GET"])
        # router.add_api_route("/draining/stop", self.stop_draining, methods=["GET"])
        # router.add_api_route("/serial_number", self.serial_number, methods=["GET"])


if __name__ == "__main__":
    chiller = HuberChiller(aioserial.AioSerial(port="COM8"))
    status = asyncio.run(chiller.status())
    print(status)
