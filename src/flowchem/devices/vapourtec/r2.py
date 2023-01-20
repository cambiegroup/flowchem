""" Control module for the Vapourtec R2 """
from __future__ import annotations

import time
from collections import namedtuple
from collections.abc import Iterable

import aioserial
import pint
from loguru import logger

from flowchem import ureg
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vapourtec.r2_components_control import (
    R2GeneralSensor,
    R2PhotoReactor,
    R2HPLCPump,
    R2InjectionValve,
    R2TwoPortValve,
    R2PumpPressureSensor,
    R2GeneralPressureSensor,
    R2MainSwitch,
)
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

    AllComponentStatus = namedtuple(
        "ComponentStatus",
        [
            "run_state",
            "pumpA_speed",
            "pumpB_speed",
            "airlock1",
            "airlock2",
            "presslimit",
            "LEDs_bitmap",
            "chan1_temp",
            "chan2_temp",
            "chan3_temp",
            "chan4_temp",
            "U1",
            "U2",
            "U3",
            "L1",
            "L2",
        ],
    )

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

        # Sets all pump to 0
        await self.set_Flowrate(0, "0 ul/min")
        await self.set_Flowrate(1, "0 ul/min")
        # Sets all temp to room temp.
        await self.set_Temperature("24°C")
        # set UV to 0%
        await self.set_UV("0", "0")
        # set max pressure to  10 bar
        await self.set_Pressure_limit("10 bar")
        # Set valve to default position
        await self.trigger_Key_Press("0")
        await self.trigger_Key_Press("2")
        await self.trigger_Key_Press("4")
        await self.trigger_Key_Press("6")
        await self.trigger_Key_Press("8")
        await self.power_on()

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
        self._serial.reset_input_buffer()  # Clear input buffer, discarding all that is in the buffer.
        await self._write(command)
        logger.debug(f"Command {command} sent to R2!")

        failure = 0
        while True:
            response = await self._read_reply()
            if not response:
                failure += 1
                logger.warning(f"{failure} time of failure!")
                # Allows 3 failures...
                if failure > 3:
                    raise InvalidConfiguration("No response received from R2 module!")
            else:
                break

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
        State_dic = {
            "0": "Off",
            "1": "Running",
            "2": "System overpressure",
            "3": "Pump A overpressure",
            "4": "Pump B overpressure",
            "5": "Underpressure(leak)",
            "6": "Pump A underpressure",
            "7": "Pump B underpressure",
        }
        state = await self.get_status()
        return State_dic[state.run_state]

    async def get_setting_Flowrate(self, pump_code: int) -> str:
        """Get pump flow rate"""
        state = await self.get_status()
        return f"{state[pump_code+1]} ul/min"

    async def get_setting_Pressure_Limit(self) -> str:
        """Get system pressure limit"""
        state = await self.get_status()
        return state.presslimit

    async def get_setting_Temperature(self) -> str:
        """Get temperature (in Celsius) from R4."""
        state = await self.get_status()
        return "Off" if state.chan3_temp == "-1000" else state.chan3_temp

    async def get_valve_Position(self, valve_code: int) -> str:
        "Get specific valves position"
        state = await self.get_status()
        # Current state of all valves as bitmap
        bitmap = int(state.LEDs_bitmap)

        return list(reversed(f"{bitmap:05b}"))[valve_code]
        # return f"{bitmap:05b}"[-(valve_code+1)]  # return 0 or 1

    # Set parameters
    async def set_Flowrate(self, pump: int, flowrate: str):
        "Set flow rate to pump"  # pump A = 0; pump B = 1
        if flowrate.isnumeric():
            flowrate = flowrate + "ul/min"
            logger.warning(
                "No units provided to set_temperature, assuming microliter/minutes."
            )
        parsed_f = ureg.Quantity(flowrate)

        cmd = self.cmd.SET_FLOWRATE.format(
            pump=str(pump), rate_in_ul_min=round(parsed_f.m_as("ul/min"))
        )
        await self.write_and_read_reply(cmd)

    async def set_Temperature(
        self, temp: str, channel: str = "2", ramp_rate: str = None
    ):
        """Set temperature to channel3: range -40 to 80°C
        Args:
            temperature (object):
        """
        if temp.isnumeric():
            temp = temp + "°C"
            logger.warning("No units provided to set_temperature, assuming Celsius.")
        set_t = ureg.Quantity(temp)

        cmd = self.cmd.SET_TEMPERATURE.format(
            channel=channel,
            temperature_in_C=round(set_t.m_as("°C")),
            ramp_rate=ramp_rate,
        )
        await self.write_and_read_reply(cmd)

    async def set_Pressure_limit(self, pressure: str):
        """set maximum system pressure: range 1,000 to 50,000 mbar"""
        if pressure.isnumeric():
            pressure = pressure + "mbar"
            logger.warning("No units provided to set_temperature, assuming mbar.")
        set_p = ureg.Quantity(pressure)

        cmd = self.cmd.SET_MAX_PRESSURE.format(
            max_p_in_mbar=round(set_p.m_as("mbar") / 500) * 500
        )
        await self.write_and_read_reply(cmd)

    async def set_UV(self, power: str = "100", heated: str = "0"):
        """set intensity of the UV light: 0 or 50 to 100"""
        cmd = self.cmd.SET_UV150.format(power_percent=power, heater_on=heated)
        await self.write_and_read_reply(cmd)

    async def trigger_Key_Press(self, keycode: str):
        """Set valve position"""
        cmd = self.cmd.KEY_PRESS.format(keycode=keycode)
        await self.write_and_read_reply(cmd)

    async def power_on(self):
        """Turn on both devices, R2 and R4."""
        await self.write_and_read_reply(self.cmd.POWER_ON)

    async def power_off(self):
        """Turn off both devices, R2 and R4."""
        await self.write_and_read_reply(self.cmd.POWER_OFF)

    async def get_current_temperature(self, channel=2) -> float:
        """Get temperature (in Celsius) from channel3."""
        state = await self.write_and_read_reply(self.cmd.HISTORY_TEMPERATURE)
        temp_state = state.split("&")[0].split(",")
        # 0: time, 5: cooling, heating, or ... 6: temp
        return float(temp_state[channel * 3]) / 10

    async def get_pressure_history(self) -> namedtuple / dict:
        """Get pressure history and returns it as [ (in mbar)"""
        # Get a `&` separated list of pressures for all sensors every second
        pressure_history = await self.write_and_read_reply(self.cmd.HISTORY_PRESSURE)
        # Each pressure data point consists of four values: time and three pressures
        _, *pressures = pressure_history[0].split(",")  # e.g. 45853,94,193,142
        # Converts to mbar
        p_in_mbar = [int(x) * 10 for x in pressures]
        return p_in_mbar[1], p_in_mbar[2], p_in_mbar[0]  # pumpA, pumpB, system

    async def get_current_pressure(self, pump_code: int = 2) -> int:
        """Get current pressure (in mbar)"""
        press_state_list = await self.get_pressure_history()
        # 0: pump A, 1: pump_B, 2: system pressure
        return press_state_list[pump_code]

    async def get_current_flow(self, pump_code: int) -> float:
        """Get current flow rate (in ul/min)"""
        state = await self.write_and_read_reply(self.cmd.HISTORY_FLOW)
        # AllState = namedtuple("flowstate", ["time", "pumpA_flow", "pumpB_flow"])
        flow_state_list = state.split("&")[0].split(",")
        # 0: time, 1: pump A, 2: pump B
        return float(flow_state_list[pump_code + 1])

    async def get_current_power(self) -> str:
        """Get power"""
        state = await self.write_and_read_reply(self.cmd.HISTORY_POWER)
        if state.find("&"):
            power_state = state.split("&")[0].split(",")
        else:
            power_state = state.split(",")
        # 0: time, 3: channel 3 power
        return power_state[3]

    async def pooling(self) -> dict:
        """extract all reaction parameters"""
        AllState = dict()
        while True:
            state = await self.get_status()
            AllState["RunState_code"] = state.run_state
            # AllState["ValveState_code"] = state.LEDs_bitmap
            AllState["allValve"] = "{0:05b}".format(int(state.LEDs_bitmap))
            # AllState["2PortValveA"] = await self.get_valve_Position(0)
            # AllState["2PortValveB"] = await self.get_valve_Position(1)
            # AllState["InjValveA"] = await self.get_valve_Position(2)
            # AllState["InjValveA"] = await self.get_valve_Position(3)
            # AllState["2PortValveC"] = await self.get_valve_Position(4)
            # AllState["sysState"] = await self.get_Run_State()
            AllState["sysP"] = await self.get_current_pressure()
            # AllState["pupmA_P"] = await self.get_current_pressure(pump_code = 0)
            # AllState["pupmB_P"] = await self.get_current_pressure(pump_code = 1)
            # AllState["pumpA_flow"] =await self.get_current_flow(pump_code=0)
            # AllState["pumpB_flow"] =await self.get_current_flow(pump_code=1)
            AllState["Temp"] = await self.get_current_temperature()
            AllState["UVpower"] = await self.get_current_power()
            # self.last_state = parse(self._serial.write_async("sdjskal"))
            # time.sleep(1)
            return AllState

    def components(self):
        # temp_limits = {
        #     ch_num: TempRange(min=ureg.Quantity(t[0]), max=ureg.Quantity(t[1]))
        #     for ch_num, t in enumerate(zip(self._min_t, self._max_t))
        # }
        list_of_components = [
            R2MainSwitch("Power", self),
            R2GeneralPressureSensor("PressureSensor", self),
            R2GeneralSensor("GSensor2", self),
            R2PhotoReactor("PhotoReactor", self),
            R2HPLCPump("Pump_A", self, 0),
            R2HPLCPump("Pump_B", self, 1),
            R2TwoPortValve("ReagentValve_A", self, 0),
            R2TwoPortValve("ReagentValve_B", self, 1),
            R2TwoPortValve("CollectionValve", self, 4),
            R2InjectionValve("InjectionValve_A", self, 2),
            R2InjectionValve("InjectionValve_B", self, 3),
            R2PumpPressureSensor("PumpSensor_A", self, 0),
            R2PumpPressureSensor("PumpSensor_B", self, 1),
        ]

        return list_of_components


if __name__ == "__main__":
    import asyncio

    Vapourtec_R2 = R2(port="COM4")

    async def main(Vapourtec_R2):
        """test function"""
        # await Vapourtec_R2.initialize()
        # Get valve and pump
        (
            r2swich,
            sysPs,
            Gs,
            pr2,
            pA,
            pB,
            vA,
            vB,
            vC,
            ivA,
            ivB,
            sA,
            sB,
        ) = Vapourtec_R2.components()

        # print(f"The system state is {await Vapourtec_R2.get_Run_State()}")
        # await Vapourtec_R2.set_Temperature("30 °C")
        # print(f"Temperature is {await Vapourtec_R2.get_setting_Temperature()}")
        # await pA.set_flowrate("100 ul/min")
        try:
            await pA.infuse("10 ul/min")
        finally:

            # print(f"current pressure of pump A is {await sA.read_pressure()}")

            # print(f"{await Vapourtec_R2.get_valve_Position(2)}")
            # print(f"Injection valve A {await ivA.get_position()}")
            # await ivA.set_position("inject")
            # await asyncio.sleep(0.5)
            # print(f"Injection valve A {await ivA.get_position()}")
            await r2swich.power_off()

    asyncio.run(main(Vapourtec_R2))
