"""
Original code from Manson website with edits.
No license originally specified.

Changes:
    * dropped Py2 support ('cause it is 2020)
    * Refactoring according to PEP8 and Zen of Python
"""

import re
from typing import Union, Literal, Tuple, Optional, List

import serial


class MansonException(Exception):
    pass


class NotConnectedError(MansonException):
    pass


class InvalidArgument(MansonException):
    pass


class InvalidOrNoReply(MansonException):
    pass


class PowerSupply:
    """ Control module for Manson Power Supply (e.g. used to power LEDs in the photo-rector or as potentiostat) """
    MODEL_ALT_RANGE = ["HCS-3102", "HCS-3014", "HCS-3204", "HCS-3202"]

    def __init__(self, com_port, baud_rate=9600):
        try:
            self._sp = serial.Serial(
                com_port,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
            )
            self._sp.reset_input_buffer()
            self._sp.reset_output_buffer()

        except serial.SerialException as e:
            print(f"Could not connect to power supply: {e}")
            raise NotConnectedError from e

        # for the unlikely case
        if self.get_info() not in self.MODEL_ALT_RANGE:
            raise InvalidOrNoReply(
                f"Device on {com_port} is either not supported or no MansonLib Device"
            )

    def close(self):
        """" Closes serial connection. """
        self._sp.close()

    def _send_command(
        self,
        command: str,
        multiline_reply: bool = False,
        no_reply_expected: bool = False,
    ) -> str:
        """ Internal function to send command and read reply. """

        # Flush buffer, write command and read reply
        try:
            self._sp.reset_input_buffer()
            self._sp.write(f"{command}\r".encode("ascii"))
            response = self._sp.readline().decode("ascii").strip()
        except serial.serialutil.SerialException:
            raise NotConnectedError("Connection seems closed")

        if not response and not no_reply_expected:
            raise InvalidOrNoReply("No reply received!")

        # Get multiple lines if needed
        if multiline_reply:
            while additional_response := self._sp.readline().decode("ascii").strip():
                response += "\n" + additional_response

        return response

    def get_info(self) -> str:
        """ Returns the model name of the connected device """
        response = self._send_command("GMOD")

        pattern = re.compile(r".*\d{4}\s")
        match = pattern.match(response)

        if match:
            if response[0:4] == "HCS-":
                return match.group().rstrip()
            return "HCS-" + match.group().rstrip()
        raise InvalidOrNoReply

    def output_on(self) -> bool:
        """ Turn on electricity on output """
        response = self._send_command("SOUT0")
        return response == "OK"

    def output_off(self) -> bool:
        """ Turn off electricity on output """
        response = self._send_command("SOUT1")
        return response == "OK"

    def get_output_read(self) -> Tuple[float, float, Literal["CC", "CV", False]]:
        """ Returns actual values of voltage, current and mode """
        response = self._send_command("GETD")

        try:
            volt = float(response[0:4]) / 100
            curr = float(response[4:8]) / 100
        except ValueError:
            raise InvalidOrNoReply

        if response[8:9] == "0":
            mode = "CV"
        elif response[8:9] == "1":
            mode = "CC"
        else:
            mode = False

        # noinspection PyTypeChecker
        return volt, curr, mode

    def get_output_voltage(self) -> float:
        """ Returns output voltage in Volt """
        return self.get_output_read()[0]

    def get_output_current(self) -> float:
        """ Returns output current in Ampere """
        return self.get_output_read()[1]

    def get_output_mode(self) -> Literal["CC", "CV"]:
        """ Returns output mode: either current control (CC) or voltage control (CV) """
        return self.get_output_read()[2]

    def get_output_power(self) -> Optional[float]:
        """ Returns output power in watts """
        voltage, intensity, _ = self.get_output_read()
        return voltage * intensity

    def get_max(self) -> Tuple[float, float]:
        """ Returns maximum voltage and current, as tuple, or False. """
        response = self._send_command("GMAX")

        max_v = int(response[0:3])
        max_c = int(response[3:6])

        if 0 <= max_v <= 999:
            max_v /= float(10)
        model = self.get_info()
        if model in self.MODEL_ALT_RANGE:
            max_c /= 10
        return max_v, max_c / float(10)

    def get_setting(self) -> Tuple[float, float]:
        """ Returns current setting as tuple (voltage, current). """
        response = self._send_command("GETS")

        # RegEx to only keep numbers
        response = re.sub(r"\D", "", response)
        v_setting = float(response[0:3]) / 10
        c_setting = float(response[3:6])

        if self.get_info() in self.MODEL_ALT_RANGE:
            c_setting /= 10

        return v_setting, c_setting / 10

    def set_voltage(self, value_in_volt: float) -> bool:
        """ Set target voltage """
        # Zero fill by left pad with zeros, up to three digits
        cmd = "VOLT" + str(value_in_volt * 10).zfill(3)

        response = self._send_command(cmd)
        return response == "OK"

    def set_current(self, current_in_ampere) -> bool:
        """ Set target current """
        if not isinstance(current_in_ampere, (int, float)):
            raise InvalidArgument

        if self.get_info() in self.MODEL_ALT_RANGE:
            cmd = "CURR" + str(current_in_ampere * 100).zfill(3)
            if current_in_ampere > 10:
                raise MansonException("Invalid current intensity for device!")
        else:
            cmd = "CURR" + str(current_in_ampere * 10).zfill(3)
            if current_in_ampere > 100:
                raise MansonException("Invalid current intensity for device!")

        response = self._send_command(cmd)
        return response == "OK"

    def set_all_preset(self, preset: List[Tuple[float, float]]) -> bool:
        """ Set all 3 preset memory position with voltage/current values """
        voltage_multiplier = 100 if self.get_info() in self.MODEL_ALT_RANGE else 10
        command = "PROM"

        for set_values in preset:
            voltage, current = set_values
            voltage_string = str(int(voltage * voltage_multiplier)).zfill(3)
            current_string = str(int(current * 10)).zfill(3)
            command += voltage_string + current_string

        # Set and verify new values (no reply from device on this command)
        self._send_command(command, no_reply_expected=True)
        return True

    def set_preset(self, index: int, voltage: float, current: float) -> bool:
        """ Set preset position index with the provided values of voltage and current """
        preset = self.get_all_preset()
        try:
            preset[index] = (voltage, current)
        except KeyError as e:
            raise InvalidArgument from e
        return self.set_all_preset(preset)

    def get_all_preset(self) -> List[Tuple[float, float]]:
        """ Get voltage and current for all 3 memory preset position """
        response_lines = self._send_command("GETM", multiline_reply=True).split("\r")

        voltage = []
        current = []

        for preset in response_lines[0:3]:
            # Drop all but numbers
            preset = re.sub(r"\D", "", preset)
            try:
                # Three digits for voltage and three digits for current
                voltage.append(float(preset[0:3]))
                current.append(float(preset[3:6]))
            except (KeyError, ValueError) as e:
                raise InvalidOrNoReply from e

        # Transform current in Ampere and voltage in Volt
        current = [x / 10 for x in current]
        voltage = [x / 10 for x in voltage]

        # Usual issue with some models having higher precision for voltage
        if self.get_info() in self.MODEL_ALT_RANGE:
            voltage = [x / 10 for x in voltage]

        return list(zip(voltage, current))

    def get_preset(self, index) -> Tuple[float, float]:
        """ Get voltage and current for given preset position [0..2] """
        all_preset = self.get_all_preset()
        try:
            return all_preset[index]
        except KeyError as e:
            raise InvalidArgument from e

    def run_preset(self, index: int) -> bool:
        """ Set Voltage and Current using values saved in one of the three memory locations: 0, 1 or 2 """
        if not 0 <= int(index) < 3:
            raise InvalidArgument
        cmd = "RUNM" + str(int(index))
        response = self._send_command(cmd)
        return response == "OK"

    def remove_protection(self) -> bool:
        """" I guess it removes over voltage protection? """
        response = self._send_command("SPRO0")
        return bool(response)

    def add_protection(self) -> bool:
        """" I guess it adds over voltage protection? """
        response = self._send_command("SPRO1")
        return bool(response)

    def set_voltage_and_current(self, voltage_in_volt: float, current_in_ampere: float):
        """ Convenience method to set both voltage and current """
        self.set_voltage(voltage_in_volt)
        self.set_current(current_in_ampere)

    def get_router(self):
        """ Creates an APIRouter for this PowerSupply instance. """
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/output/on", self. output_on, methods=["GET"])
        router.add_api_route("/output/off", self.output_off, methods=["GET"])
        router.add_api_route("/output/power", self.get_output_power, methods=["GET"])
        router.add_api_route("/output/mode", self.get_output_mode, methods=["GET"])
        router.add_api_route("/voltage/read", self.get_output_voltage, methods=["GET"])
        router.add_api_route("/voltage/max", self.set_voltage, methods=["PUT"])
        router.add_api_route("/current/read", self.get_output_current, methods=["GET"])
        router.add_api_route("/current/max", self.set_current, methods=["PUT"])
        router.add_api_route("/protection/add", self.add_protection, methods=["GET"])
        router.add_api_route("/protection/remove", self.remove_protection, methods=["GET"])

        return router
