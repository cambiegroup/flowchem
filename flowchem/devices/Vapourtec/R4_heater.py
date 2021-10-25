import time
from typing import Tuple

import aioserial
import logging

from flowchem.constants import DeviceError, InvalidConfiguration

try:
    from flowchem.devices.Vapourtec.commands import R4Command, VapourtecCommand
except ImportError as e:
    raise PermissionError(
        "Cannot redistribute Vapourtec commands... Contact Vapourtec to get them!"
    ) from e


class R4Heater:
    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 19200,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    """ Virtual control of the Vapourtec R4 heating module. """
    def __init__(self, **config):
        # Merge default settings, including serial, with provided ones.
        configuration = dict(R4Heater.DEFAULT_CONFIG, **config)
        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as e:
            raise InvalidConfiguration(f"Cannot connect to the R4Heater on the port <{config.get('port')}>") from e

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)

    async def _write(self, command: str):
        """ Writes a command to the pump """
        cmd = command + "\r\n"
        await self._serial.write_async(cmd.encode("ascii"))
        self.logger.debug(f"Sent command: {repr(command)}")

    async def _read_reply(self) -> str:
        """ Reads the pump reply from serial communication """
        reply_string = await self._serial.readline_async()
        self.logger.debug(f"Reply received: {reply_string.decode('ascii')}")
        return reply_string.decode("ascii")

    def parse_response(self, response: str) -> Tuple[bool, str]:
        """ Split a received line in its components: success, reply """
        try:
            if response[0:2] != "ER":
                return True, response.rstrip()
            else:
                return False, response.rstrip()
        except KeyError:
            raise DeviceError(f"Invalid reply {response}")

    async def write_and_read_reply(self, command: R4Command) -> str:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        self._serial.reset_input_buffer()
        await self._write(command.compile())
        response = await self._read_reply()

        if not response:
            raise InvalidConfiguration("No response received from heating module!")

        # Parse reply
        success, parsed_response = self.parse_response(response)

        return parsed_response

    async def wait_for_target_temp(self, channel: int):
        """ Waits until the target channel has reached the desired temperature and is stable """
        t_stable = False
        failure = 0
        while not t_stable:
            try:
                ret_code = await self.write_and_read_reply(
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

    async def set_temperature(self, channel, target_temperature: int, wait: bool = False):
        """ Set temperature and optionally waits for S """
        set_command = getattr(VapourtecCommand, f"SET_CH{channel}_TEMP")
        # Float not accepted, must cast to int
        await self.write_and_read_reply(set_command.set_argument(int(target_temperature)))
        # Set temperature implies channel on
        await self.write_and_read_reply(VapourtecCommand.CH_ON.set_argument(channel))

        if wait:
            await self.wait_for_target_temp(channel)

    def get_router(self):
        """ Creates an APIRouter for this object. """
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/temperature/set", self.set_temperature, methods=["PUT"])

        return router


if __name__ == "__main__":
    import asyncio
    heat = R4Heater.from_config(dict(port="COM11"))

    async def main():
        await heat.set_temperature(0, 30, wait=False)
        print("not waiting")
        await heat.set_temperature(0, 30, wait=True)
        print("actually I waited")

    asyncio.run(main())
