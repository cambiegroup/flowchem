""" Control module for the Vapourtec R2 """
from __future__ import annotations

import time
from collections import namedtuple
from collections.abc import Iterable

import aioserial
import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.technical.temperature import TempRange
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vapourtec.r4_heater_channel_control import R4HeaterChannelControl
from flowchem.utils.exceptions import InvalidConfiguration
from flowchem.utils.people import *

try:
    from flowchem_vapourtec import VapourtecR2Commands

    HAS_VAPOURTEC_COMMANDS = True
except ImportError:
    HAS_VAPOURTEC_COMMANDS = False


class R2(FlowchemDevice):
    """R2 reactor module class."""

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 19200,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    AllComponentStatus = namedtuple("ComponentStatus",
                                    ["run_state", "pumpA_speed", "pumpB_speed",
                                     "airlock1", "airlock2",
                                     "presslimit", "LEDs_bitmap",
                                     "chan1_temp", "chan2_temp", "chan3_temp", "chan4_temp",
                                     "U1", "U2", "U3", "L1","L2"
                                    ])

    def __init__(
        self,
        name: str = "",
        min_temp: float | list[float] = -40,
        max_temp: float | list[float] = 80,
        # min_pressure: float
        # max_pressure: float
        **config,
    ):
        super().__init__(name)

        # Set max pressure for R2 pump



        # Set min and max temp for R4 heater
        if not isinstance(min_temp, Iterable):
            min_temp = [min_temp] * 4
        if not isinstance(max_temp, Iterable):
            max_temp = [max_temp] * 4
        assert len(min_temp) == len(max_temp) == 4
        self._min_t = min_temp
        self._max_t = max_temp

        if not HAS_VAPOURTEC_COMMANDS:
            raise InvalidConfiguration(
                "You tried to use a Vapourtec device but the relevant commands are missing!\n"
                "Unfortunately, we cannot publish those as they were provided under NDA.\n"
                "Contact Vapourtec for further assistance."
            )

        self.cmd = VapourtecR2Commands()

        # Merge default settings, including serial, with provided ones.
        configuration = R2.DEFAULT_CONFIG | config
        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as ex:
            raise InvalidConfiguration(
                f"Cannot connect to the R2 on the port <{config.get('port')}>"
            ) from ex

        self.metadata = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="Vapourtec",
            model="R2 reactor module",
        )

    async def initialize(self):
        """Ensure connection."""
        self.metadata.version = await self.version()
        logger.info(f"Connected with R2 version {self.metadata.version}")

    async def _write(self, command: str):
        """Writes a command to the pump"""
        cmd = command + "\r\n"
        await self._serial.write_async(cmd.encode("ascii"))
        logger.debug(f"Sent command: {repr(command)}")

    async def _read_reply(self) -> str:
        """Reads the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.debug(f"Reply received: {reply_string.decode('ascii').rstrip()}")
        return reply_string.decode("ascii")

    async def write_and_read_reply(self, command: str) -> str:
        """Sends a command to the pump, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer() #Clear input buffer, discarding all that is in the buffer.
        await self._write(command)
        logger.debug(f"Command {command} sent to R2!")
        response = await self._read_reply()

        if not response:
            raise InvalidConfiguration("No response received from heating module!")

        logger.debug(f"Reply received: {response}")
        return response.rstrip()


    #Specific Commands
    async def version(self):
        """Get firmware version."""
        return await self.write_and_read_reply(self.cmd.VERSION)


    async def system_type(self):
        """Get system type: system type, pressure mode"""
        return await self.write_and_read_reply(self.cmd.GET_SYSTEM_TYPE)
    async def get_status(self) -> AllComponentStatus:
        """Get all status from R2."""
        failure = 0
        while True:
            try:
                raw_status = await self.write_and_read_reply(self.cmd.GET_STATUS)
                return R2.AllComponentStatus._make(raw_status.split(" "))

            except InvalidConfiguration as ex:
                failure += 1
                # Allows 3 failures cause the R2 is choosy at times...
                if failure > 3:
                    raise ex
                else:
                    continue

    async def get_Run_State(self) -> str:
        """Get run state"""
        State_dic ={
            "0":"Off",
            "1": "Running",
            "2": "System overpressure",
            "3": "Pump A overpressure",
            "4": "Pump B overpressure",
            "5": "Underpressure(leak)",
            "6": "Pump A underpressure",
            "7": "Pump B underpressure"
        }
        state = await self.get_status()
        return State_dic[state.run_state]
    async def get_flowrate(self):
        """Get pump flow rate"""

    async def get_pressure_limit(self):
        """Get pressure limit"""

    async def get_valve_position(self):
        "Get valve position"


    async def

    async def set_temperature(self, channel, temperature: pint.Quantity):
        """Set temperature to channel3."""
        cmd = self.cmd.SET_TEMPERATURE.format(
            channel=channel, temperature_in_C=round(temperature.m_as("°C"))
        )
        await self.write_and_read_reply(cmd)
        # Set temperature implies channel on
        await self.power_on(channel)
        # Verify it is not unplugged
        status = await self.get_status(channel)
        if status.state == "U":
            logger.error(
                f"TARGET CHANNEL {channel} UNPLUGGED! (Note: numbering starts at 0)"
            )

    async def get_temperature(self, channel):
        """Get temperature (in Celsius) from channel."""
        state = await self.get_status(channel)
        return None if state.temperature == "281.2" else state.temperature

    async def power_on(self, channel):
        """Turn on channel."""
        await self.write_and_read_reply(self.cmd.POWER_ON.format(channel=channel))

    async def power_off(self, channel):
        """Turn off channel."""
        await self.write_and_read_reply(self.cmd.POWER_OFF.format(channel=channel))

    def pooling(self):
        while True:
            self.last_state = parse(self._serial.write_async("sdjskal"))
            # save to file
            time.sleep(1)

    def components(self):
        temp_limits = {
            ch_num: TempRange(min=ureg.Quantity(t[0]), max=ureg.Quantity(t[1]))
            for ch_num, t in enumerate(zip(self._min_t, self._max_t))
        }
        list_of_components = [
            R4HeaterChannelControl(f"reactor{n+1}", self, n, temp_limits[n])
            for n in range(4)
        ]

        list_of_components.append(R2InjectionValveA)
        list_of_components.append(R2InjectionValveB)
        list_of_components.append(R2PumpA)
        list_of_components.append(R2PumpB)

        return list_of_components


if __name__ == "__main__":
    import asyncio

    Vapourtec_R2 = R2(port="COM4")

    async def main(heat):
        """test function"""
        await Vapourtec_R2.initialize()
        # # Get reactors
        # r1, r2, r3, r4 = heat.components()

        # await r1.set_temperature("30 °C")
        print(f"Temperature is {await r1.get_temperature()}")

    asyncio.run(main(heat))
