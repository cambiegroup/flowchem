"""
Original code from Manson website with edits.
No license originally specified.

Changes:
    * dropped Py2 support ('cause it is 2020)
    * Refactoring according to PEP8 and Zen of Python
"""

import re
import operator
from typing import Union, Literal, Tuple, Optional
import serial


class MansonException(Exception):
    pass


class NotConnectedError(MansonException):
    pass


class InvalidArgument(MansonException):
    pass


class InstrumentInterface:
    MODEL_ALT_RANGE = ['HCS-3102', 'HCS-3014', 'HCS-3204']

    def __init__(self):
        self.sp = None

    def open(self, com_port, baud_rate=9600):
        """ Opens serial connection. """
        if baud_rate not in serial.serialutil.SerialBase.BAUDRATES:
            return MansonException(f"Invalid baud rate provided {baud_rate}!")
        try:
            self.sp = serial.Serial(com_port, baudrate=baud_rate, bytesize=8, parity='N', stopbits=1, timeout=0.1)
            self.sp.reset_input_buffer()
            self.sp.reset_output_buffer()

        except serial.SerialException as e:
            print(f"Could not connect to power supply: {e}")
            self.sp = None
            return False

        return True

    def close(self):
        """" Closes serial connection. """
        if self.sp is not None:
            self.sp.close()
            self.sp = None
            return True
        return False

    def _send_command(self, command: str) -> str:
        """ Internal function to send command and read reply. """
        if self.sp is None:
            raise NotConnectedError
        self.sp.reset_input_buffer()
        self.sp.write(f"{command}\r".encode('ascii'))
        return self.sp.readline().decode('ascii').strip()

    def get_info(self):
        response = self._send_command("GMOD")
        if not response:
            return False

        pattern = re.compile(r'.*\d{4}\s')
        match = pattern.match(response)

        if match:
            if response[0:4] == "HCS-":
                return match.group().rstrip()
            return "HCS-" + match.group().rstrip()
        return False

    def output_on(self):
        response = self._send_command("SOUT0")
        return response == "OK"

    def output_off(self):
        response = self._send_command("SOUT1")
        return response == "OK"

    def get_output_read(self) -> Union[bool, Tuple[float, float, Literal["CC", "CV", False]]]:
        """ Returns actual values of voltage, current and mode """
        response = self._send_command("GETD")
        if not response:
            return False

        try:
            volt = float(response[0:4]) / 100
            curr = float(response[4:8]) / 100
        except ValueError:
            return False

        if response[8:9] == '0':
            mode = "CV"
        elif response[8:9] == '1':
            mode = "CC"
        else:
            mode = False

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
        if self.sp is not None:
            try:
                voltage, intensity, _ = self.get_output_read()
                return voltage * intensity
            except TypeError:
                return False
        return False

    def get_max(self) -> Union[bool, Tuple[float, float]]:
        """ Returns maximum voltage and current, as tuple, or False. """
        response = self._send_command("GMAX")
        if not response:
            return False

        max_v = int(response[0:3])
        max_c = int(response[3:6])

        if 0 <= max_v <= 999:
            max_v /= float(10)
        model = self.get_info()
        if model in self.MODEL_ALT_RANGE:
            max_c /= 10
        return max_v, max_c / float(10)

    def get_setting(self) -> Union[bool, Tuple[float, float]]:
        """ Returns current setting as tuple (voltage, current). """
        response = self._send_command("GETS")
        if not response:
            return False

        response = re.sub(r"\D", "", response)
        v_setting = float(response[0:3]) / 10
        c_setting = float(response[3:6])

        model = self.get_info()
        if model in self.MODEL_ALT_RANGE:
            c_setting /= 10

        return v_setting, c_setting / 10

    def set_voltage(self, value_in_volt: Union[int, float]):
        """ Set target voltage """
        # Zero fill by left pad with zeros, up to three digits
        cmd = "VOLT" + str(value_in_volt * 10).zfill(3)

        response = self._send_command(cmd)
        return response == "OK"

    def set_current(self, current_in_ampere):
        if not isinstance(current_in_ampere, (int, float)):
            raise InvalidArgument

        model = self.get_info()
        if model in self.MODEL_ALT_RANGE:
            cmd = "CURR" + str(current_in_ampere * 100).zfill(3)
            if current_in_ampere > 10:
                return MansonException("Invalid current intensity for device!")
        else:
            cmd = "CURR" + str(current_in_ampere * 10).zfill(3)
            if current_in_ampere > 100:
                return MansonException("Invalid current intensity for device!")

        response = self._send_command(cmd)
        return response == "OK"

    def Pset(self, num: int, volt, curr):
        if isinstance(num, int):
            num_max = 3
            if num > num_max - 1 or num < 0:
                return False
            for x in range(num_max):
                if x == num:
                    index = num + x
                    break
        model_list = ['HCS-3102', 'HCS-3014', 'HCS-3204']
        list_c = ['3', '6', '10', '13', '17', '20']
        response = self._send_command("GETM")

        if not response:
            return False
        response = list(response)
        if isinstance(volt, (int, float)):
            list_v = ['0', '3', '7', '10', '14', '17']
            if 0 <= volt < 1:
                volt = int(volt * 10)
                response[(int(list_v[index])):(int(list_v[index + 1]))] = '00' + str(volt)
            elif 1 <= volt < 10:
                volt = int(volt * 10)
                response[(int(list_v[index])):(int(list_v[index + 1]))] = '0' + str(volt)
            elif 10 <= volt < 100:
                volt = int(volt * 10)
                response[(int(list_v[index])):(int(list_v[index + 1]))] = str(volt)
            else:
                return False
        model = self.get_info()
        model_mark = 0
        if model == '':
            return False
        if isinstance(curr, (int, float)):
            for model_ in model_list:
                if operator.eq(model[0:8], model_) == 1:
                    if 0 <= curr < 1:
                        curr = int(curr * 100)
                        response[(int(list_c[index])):(int(list_c[index + 1]))] = '0' + str(curr)
                    elif 1 <= curr < 10:
                        curr = int(curr * 100)
                        response[(int(list_c[index])):(int(list_c[index + 1]))] = str(curr)
                    else:
                        return False
                    model_mark = 1
                    break
        else:
            return False
        if model_mark == 0:
            if 0 <= curr < 1:
                curr = int(curr * 10)
                response[(int(list_c[index])):(int(list_c[index + 1]))] = '00' + str(curr)
            elif 1 <= curr < 10:
                curr = int(curr * 10)
                response[(int(list_c[index])):(int(list_c[index + 1]))] = '0' + str(curr)
            elif 10 <= curr < 99:
                curr = int(curr * 10)
                response[(int(list_c[index])):(int(list_c[index + 1]))] = str(curr)
            else:
                return False
        response = ''.join(response)
        response = response[0:6] + response[7:13] + response[14:20]
        cmd = 'PROM' + response
        response = self._send_command(cmd)
        if not response:
            return False
        return response

    def GPset(self, index, option):
        model_list = ['HCS-3102', 'HCS-3014', 'HCS-3204']
        model = self.get_info()
        model_mark = 0
        list_v = ['0', '3', '6', '9', '12', '15']
        list_c = ['3', '6', '9', '12', '15', '18']
        max_index = 3
        if isinstance(index, (int, float)) and (
            index < 0 or index > max_index - 1
        ):
            return False
        for x in range(max_index):
            if x == index:
                index = index + x
                break
        response = self._send_command("GETM")
        if not response:
            return False
        response = re.sub(r"\D", "", response)
        if option == 'A':
            volt = int(response[(int(list_v[index])):(int(list_v[index + 1]))]) / float(10)
            for model__ in model_list:
                if operator.eq(model[0:8], model__) == 1:
                    curr = int(response[(int(list_c[index])):(int(list_c[index + 1]))]) / float(100)
                    return str(volt) + " " + str(curr)
            curr = int(response[(int(list_c[index])):(int(list_c[index + 1]))]) / float(10)
            return str(volt) + " " + str(curr)
        elif option == 'C':
            for model_ in model_list:
                if operator.eq(model[0:8], model_) == 1:
                    curr = int(response[(int(list_c[index])):(int(list_c[index + 1]))]) / float(100)
                    return curr
            curr = int(response[(int(list_c[index])):(int(list_c[index + 1]))]) / float(10)
            return curr
        elif option == 'V':
            volt = int(response[(int(list_v[index])):(int(list_v[index + 1]))]) / float(10)
            return volt

    def RPreset(self, index: int) -> bool:
        """ Reset one of the preset position: 0, 1 or 2 """
        if not 0 <= int(index) < 3:
            raise InvalidArgument
        cmd = 'RUNM' + str(int(index))
        response = self._send_command(cmd)
        if not response:
            return False
        return response

    def remove_protection(self) -> bool:
        """" I guess it removes over voltage protection """
        response = self._send_command("SPRO0")
        return bool(response)

    def add_protection(self) -> bool:
        """" I guess it adds over voltage protection """
        response = self._send_command("SPRO1")
        return bool(response)


if __name__ == '__main__':
    pass
