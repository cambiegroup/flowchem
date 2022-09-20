""" Control module for the Vapourtec R4 heater """
import time
from typing import Optional

import aioserial
from flowchem.exceptions import InvalidConfiguration
from flowchem.models.base_device import BaseDevice
from flowchem.units import flowchem_ureg
from loguru import logger

try:
    from devices import (
        R4Command,
        VapourtecCommand,
    )

    HAS_VAPOURTEC_COMMANDS = True
except ImportError as e:
    HAS_VAPOURTEC_COMMANDS = False


class R4Heater(BaseDevice):
    """R4 reactor heater control class."""

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 19200,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }
    """ Virtual control of the Vapourtec R4 heating module. """

    def __init__(self, name: Optional[str] = None, **config):
        super().__init__(name)
        if not HAS_VAPOURTEC_COMMANDS:
            raise InvalidConfiguration(
                "R4Heater unusable: no Vapourtec Commands available.\n"
                "Contact your distributor to get the serial API documentation."
            )

        # Merge default settings, including serial, with provided ones.
        configuration = dict(R4Heater.DEFAULT_CONFIG, **config)
        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as ex:
            raise InvalidConfiguration(
                f"Cannot connect to the R4Heater on the port <{config.get('port')}>"
            ) from ex

    async def _write(self, command: str):
        """Writes a command to the pump"""
        cmd = command + "\r\n"
        await self._serial.write_async(cmd.encode("ascii"))
        logger.debug(f"Sent command: {repr(command)}")

    async def _read_reply(self) -> str:
        """Reads the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.debug(f"Reply received: {reply_string.decode('ascii')}")
        return reply_string.decode("ascii")

    async def write_and_read_reply(self, command: "R4Command") -> str:
        """Sends a command to the pump, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write(command.compile())
        response = await self._read_reply()

        if not response:
            raise InvalidConfiguration("No response received from heating module!")

        return response.rstrip()

    async def is_target_temp_reached(self, channel: int) -> bool:
        """Checks if the target temperature has been reached.

        Args:
            channel: channel number
        """
        failure = 0
        while True:
            try:
                ret_code = await self.write_and_read_reply(
                    VapourtecCommand.TEMP.set_argument(str(channel))
                )
            except InvalidConfiguration as ex:
                failure += 1
                # Allows 3 failures cause the R4 is choosy at times...
                if failure > 3:
                    raise ex
                else:
                    continue

            return ret_code[:1] == "S"

    async def wait_for_target_temp(self, channel: int):
        """Waits until the target channel has reached the desired temperature and is stable."""
        t_stable = False
        failure = 0
        while not t_stable:
            if not self.is_target_temp_reached(channel):
                time.sleep(1)

    async def set_temperature(
        self, channel, target_temperature: str, wait: bool = False
    ):
        """Set temperature and optionally waits for S."""
        set_command = getattr(VapourtecCommand, f"SET_CH{channel}_TEMP")

        set_temperature = flowchem_ureg(target_temperature)
        # Float not accepted, must cast to int
        await self.write_and_read_reply(
            set_command.set_argument(round(set_temperature.m_as("°C")))
        )
        # Set temperature implies channel on
        await self.write_and_read_reply(VapourtecCommand.CH_ON.set_argument(channel))

        if wait:
            await self.wait_for_target_temp(channel)

    def get_router(self):
        """Creates an APIRouter for this object."""
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/temperature/set", self.set_temperature, methods=["PUT"])
        router.add_api_route(
            "/temperature/stable", self.is_target_temp_reached, methods=["GET"]
        )

        return router


if __name__ == "__main__":
    import asyncio

    heat = R4Heater(port="COM11")

    async def main():
        """test function"""
        # noinspection PyArgumentEqualDefault
        await heat.set_temperature(0, "30 °C", wait=False)
        print("not waiting - default behaviour.")
        await heat.set_temperature(0, "30 °C", wait=True)
        print("actually I waited")

    asyncio.run(main())
