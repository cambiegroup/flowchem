import io
import time
from typing import Union, Tuple

import serial
import logging
import threading

from serial import PARITY_NONE, STOPBITS_ONE, EIGHTBITS

try:
    from flowchem.devices.Vapourtec.commands import R4Command, VapourtecCommand
except ImportError as e:
    raise PermissionError(
        "Cannot redistribute Vapourtec commands... Contact them to get it!"
    ) from e


class R4Exception(Exception):
    pass


class InvalidConfiguration(R4Exception):
    pass


class R4Heater:
    def __init__(self, port: Union[int, str]):
        if isinstance(port, int):
            port = f"COM{port}"

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.lock = threading.Lock()

        try:
            # noinspection PyPep8
            self._serial = serial.Serial(
                port=port,
                baudrate=19200,
                parity=PARITY_NONE,
                stopbits=STOPBITS_ONE,
                bytesize=EIGHTBITS,
                timeout=0.1,
            )  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration(
                f"Check serial port availability! [{port}]"
            ) from e

        self.sio = io.TextIOWrapper(
            buffer=io.BufferedRWPair(self._serial, self._serial),
            line_buffering=True,
            newline="\r\n",
        )

    def _write(self, command: str):
        """ Writes a command to the pump """
        self.logger.debug(f"Sending {repr(command)}")
        try:
            self.sio.write(command + "\r\n")
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration from e

    def _read_reply(self) -> str:
        """ Reads the pump reply from serial communication """
        reply_string = self.sio.readline()
        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def parse_response(self, response: str) -> Tuple[bool, str]:
        """ Split a received line in its components: success, reply """
        try:
            if response[0:2] != "ER":
                return True, response.rstrip()
            else:
                return False, response.rstrip()
        except KeyError:
            raise R4Exception(f"Invalid reply {response}")

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        try:
            self._serial.reset_input_buffer()
        except serial.PortNotOpenError as e:
            raise InvalidConfiguration from e

    def write_and_read_reply(self, command: R4Command) -> str:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        with self.lock:
            self.reset_buffer()
            self._write(command.compile())
            response = self._read_reply()

        if not response:
            raise InvalidConfiguration(f"No response received from heating module!")

        # Parse reply
        success, parsed_response = self.parse_response(response)

        return parsed_response

    def wait_for_target_temp(self, channel: int):
        """ Waits until the target channel has reached the desired temperature and is stable """
        t_stable = False
        failure = 0
        while not t_stable:
            try:
                ret_code = self.write_and_read_reply(
                    VapourtecCommand.TEMP.set_argument(channel)
                )
            except InvalidConfiguration as e:
                ret_code = "N"
                failure += 1
                if failure > 3:
                    raise e
            else:
                failure = 0

            if ret_code[:1] == "S":
                self.logger.debug(f"Target temperature reached on channel {channel}!")
                t_stable = True
            else:
                time.sleep(1)

    def set_temperature(self, channel, target_temperature: int, wait: bool = False):
        """ Set temperature and optionally waits for S """
        set_command = getattr(VapourtecCommand, f"SET_CH{channel}_TEMP")
        self.write_and_read_reply(
            set_command.set_argument(int(target_temperature))
        )  # int casting imp! np.float fails
        self.write_and_read_reply(VapourtecCommand.CH_ON.set_argument(channel))

        if wait:
            self.wait_for_target_temp(channel)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    heat = R4Heater(11)
    heat.set_temperature(0, 30, wait=False)
    print("not waiting")
    heat.set_temperature(0, 30, wait=True)
    print("actually I waited")

    breakpoint()
