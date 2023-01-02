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
from flowchem.devices.vapourtec.r2_components_control import R2Main, R2HPLCPump, R2InjectionValve, R2TwoPortValve
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
        min_pressure: float = 1000,
        max_pressure: float = 50000,
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


    # Specific Commands
    # Get instrument information
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

    # Get specific state of individual component
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


    async def get_setting_Flowrate(self, pump_code:int) -> pint.Quantity:  #pumpA:"0", pumpB:"1"
        """Get pump flow rate"""
        state = await self.get_status()
        return state[pump_code+1].to("ul/min")
    async def get_setting_Pressure_Limit(self) -> str:
        """Get system pressure limit"""
        state = await self.get_status()
        return state.presslimit

    async def get_setting_Temperature(self, channel = 2)-> str:
        # TODO: test which channel is enable to use
        """Get temperature (in Celsius) from R4."""
        state = await self.get_status()
        #check others channel can also be used with R2
        return "Off" if state.chan3_temp == "-1000" else state.chan3_temp
    async def get_valve_Position(self, valve_code:int)-> str:
        "Get specific valves position"
        state = await self.get_status()
        return "{0:05b}".format(int(state.LEDs_bitmap))[-(valve_code+1)]  # return 0 or 1

    # Set parameters
    async def set_Flowrate(self, pump:int , flowrate: pint.Quantity):
        "Set flowrate to pump"   # pump A = 0; pump B = 1
        cmd =self.cmd.SET_FLOWRATE.format(
            pump=str(pump), rate_in_ul_min=round(flowrate.m_as("ul/min"))
        )
        await self.write_and_read_reply(cmd)

    # async def set_Temperature(self, channel="2", temp: pint.Quantity):
    #     TODO: check others channel can also be used with R2
    #     TODO: Current Commands did not worked, check with Vapourtec
    #     """Set temperature to channel3.
    #
    #     Args:
    #         temperature (object):
    #     """
    #     cmd = self.cmd.SET_TEMPERATURE.format(
    #         channel=channel, temperature_in_C=round(temperature.m_as("°C"))
    #     )
    #     await self.write_and_read_reply(cmd)
    async def set_Pressure(self, pressure: pint.Quantity):
        """set maximum system pressure: range 1,000 to 50,000 mbar"""
        cmd = self.cmd.SET_MAX_PRESSURE.format(
            max_p_in_mbar=round(pressure.m_as("mbar")/500)*500
        )
        await self.write_and_read_reply(cmd)
    async def set_UV(self, power:str = "100",heated: str = "0"):
        """set intensity of the UV light: 0 or 50 to 100"""
        cmd = self.cmd.SET_UV150.format(
            power_percent=power, heated_on= heated
        )
        await self.write_and_read_reply(cmd)

    async def trigger_Key_Press(self, keycode:str):
        """Set valve position"""
        cmd= self.cmd.KEY_PRESS.format(keycode=keycode)
        await self.write_and_read_reply(cmd)

    async def power_on(self):
        """Turn on both devices, R2 and R4."""
        await self.write_and_read_reply(self.cmd.POWER_ON)
    async def power_off(self):
        """Turn off both devices, R2 and R4."""
        await self.write_and_read_reply(self.cmd.POWER_OFF)

    async def get_current_temperature(self, channel =2):
        # TODO: channel ckeck
        """Get temperature (in Celsius) from channel3."""
        state = await self.write_and_read_reply(self.cmd.HISTORY_TEMPERATURE)
        temp_state = state.split("&")[0].split(",")
        return temp_state[0], temp_state[channel*2+1], float(temp_state[channel*3])/10

    async def get_current_pressure(self) :
        """Get current pressure (in mbar)"""
        state = await self.write_and_read_reply(self.cmd.HISTORY_PRESSURE)
        press_state = state.split("&")[0].split(",")
        return press_state[0], press_state[1], press_state[2]

    async def get_current_flow(self) -> namedtuple :
        """Get current flow rate (in ul/min)"""
        state = await self.write_and_read_reply(self.cmd.HISTORY_FLOW)
        AllState = namedtuple("flowstate", ["time", "pumpA_flow", "pumpB_flow"])
        return AllState._make(state.split("&")[0].split(","))
        # return press_state[0], press_state[1], press_state[2] # time, pumpA_flow

    async def get_current_power(self):
        """Get power"""
        state = await self.write_and_read_reply(self.cmd.HISTORY_POWER)
        if state.find("&"):
            power_state = state.split("&")[0].split(",")
        else:
            power_state = state.split(",")
        return power_state[0], power_state[3] #time, channel 3 power



    async def pooling(self):
        while True:
            # TODO: database or  csv save record
            await self.get_Run_State()
            await self.get_current_pressure()
            await self.get_current_flow()
            await self.get_current_temperature()
            await self.get_current_power()

            # self.last_state = parse(self._serial.write_async("sdjskal"))
            # save to file
            time.sleep(1)

    def components(self):
        # temp_limits = {
        #     ch_num: TempRange(min=ureg.Quantity(t[0]), max=ureg.Quantity(t[1]))
        #     for ch_num, t in enumerate(zip(self._min_t, self._max_t))
        # }
        list_of_components = [R2Main(),
                              R2HPLCPump("HPLCPump_A", self, 0), R2HPLCPump("HPLCPump_B", self, 1),
                              R2TwoPortValve("TwoPortValve_A", self, 0),R2TwoPortValve("TwoPortValve_B", self, 1),
                              R2TwoPortValve("TwoPortValve_C", self, 4),
                              R2InjectionValve("InjectionVavle_A", self, 2), R2InjectionValve("InketionValve_B", self, 3)
        ]

        return list_of_components


if __name__ == "__main__":
    import asyncio

    Vapourtec_R2 = R2(port="COM4")

    async def main(Vapourtec_R2):
        """test function"""
        await Vapourtec_R2.initialize()
        # Get
        r2,pA, pA, vA, vB, vC, ivA, ivB = Vapourtec_R2.components()

        # await r1.set_temperature("30 °C")
        # print(f"Temperature is {await r1.get_temperature()}")

    asyncio.run(main(Vapourtec_R2))
