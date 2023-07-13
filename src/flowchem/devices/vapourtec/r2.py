""" Control module for the Vapourtec R2 """
from __future__ import annotations

from asyncio import Lock
from collections import namedtuple
from collections.abc import Iterable

import aioserial
import pint
import asyncio
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vapourtec.r2_components_control import (
    R2GeneralSensor,
    UV150PhotoReactor,
    R2HPLCPump,
    R2InjectionValve,
    R2TwoPortValve,
    R2PumpPressureSensor,
    R2GeneralPressureSensor,
    R2MainSwitch,
    R4Reactor,
)
from flowchem.components.technical.temperature import TempRange
from flowchem.utils.exceptions import InvalidConfiguration
from flowchem.utils.people import dario, jakob, wei_hsin

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
        "AllComponentStatus",
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

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Vapourtec",
            model="R2 reactor module",
        )
        self._serial_lock = Lock()

    async def initialize(self):
        """Ensure connection."""
        self.device_info.version = await self.version()
        logger.info(f"Connected with R2 version {self.device_info.version}")

        # Sets all pump to 0 ml/min
        await asyncio.sleep(0.1)
        await self.set_flowrate("A", "0 ul/min")
        await self.set_flowrate("B", "0 ul/min")
        # Sets all temp to room temp.
        rt = ureg("20 °C")
        await self.set_temperature(0, rt)
        await self.set_temperature(1, rt)
        await self.set_temperature(2, rt)
        await self.set_temperature(3, rt)
        # set UV to 0%
        await self.set_UV150(power=0, heated=False)
        # set max pressure to  10 bar
        await self.set_pressure_limit("10 bar")
        # Set valve to default position
        await self.trigger_key_press("0")
        await self.trigger_key_press("2")
        await self.trigger_key_press("4")
        await self.trigger_key_press("6")
        await self.trigger_key_press("8")
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
        async with self._serial_lock:
            await self._write(command)
            logger.debug(f"Command {command} sent to R2!")

            failure = 0
            while True:
                response = await self._read_reply()
                if not response:
                    failure += 1
                    logger.warning(f"{failure} time of failure!")
                    logger.error(f"Command {command} is not working")
                    await asyncio.sleep(0.2)
                    self._serial.reset_input_buffer()
                    await self._write(command)
                    # Allows 4 failures...
                    if failure > 3:
                        raise InvalidConfiguration(
                            "No response received from R2 module!"
                        )
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
        raw_status = await self.write_and_read_reply(self.cmd.GET_STATUS)
        if raw_status == "OK":
            logger.warning("ValueError:the reply of get status command is OK..")
            return await self.get_status()
        return R2.AllComponentStatus._make(raw_status.split(" "))

    # Get specific state of individual component
    async def get_state(self) -> str:
        """Get run state."""
        State_dic = {
            "0": "Off",
            "1": "Running",
            "2": "System overpressure",
            "3": "Pump A overpressure",
            "4": "Pump B overpressure",
            "5": "System pressure loss",
            "6": "Pump A pressure loss",
            "7": "Pump B pressure loss",
        }
        state = await self.get_status()
        return State_dic[state.run_state]

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
    async def set_flowrate(self, pump: str, flowrate: str):
        """Set flow rate to pump ('A'|'B')."""
        if flowrate.isnumeric():
            flowrate = flowrate + "ul/min"
            logger.warning(
                "No units provided to set_temperature, assuming microliter/minutes."
            )
        parsed_f = ureg.Quantity(flowrate)

        if pump == "A":
            pump_num = 0
        elif pump == "B":
            pump_num = 1
        else:
            logger.warning(f"Invalid pump name: {pump}")
            return None

        cmd = self.cmd.SET_FLOWRATE.format(
            pump=pump_num, rate_in_ul_min=round(parsed_f.m_as("ul/min"))
        )
        await self.write_and_read_reply(cmd)

    async def set_temperature(
        self, channel: int, temp: pint.Quantity, ramp_rate: str | None = None
    ):
        """Set temperature to R4 channel. If a UV150 is present then channel 3 range is limited to -40 to 80 °C."""
        cmd = self.cmd.SET_TEMPERATURE.format(
            channel=channel,
            temperature_in_C=round(temp.m_as("°C")),
            ramp_rate=ramp_rate,
        )
        await self.write_and_read_reply(cmd)

    async def set_pressure_limit(self, pressure: str):
        """set maximum system pressure: range 1,000 to 50,000 mbar"""
        if pressure.isnumeric():
            pressure = pressure + "mbar"
            logger.warning("No units provided to set_temperature, assuming mbar.")
        set_p = ureg.Quantity(pressure)

        cmd = self.cmd.SET_MAX_PRESSURE.format(
            max_p_in_mbar=round(set_p.m_as("mbar") / 500) * 500
        )
        await self.write_and_read_reply(cmd)

    async def set_UV150(self, power: int, heated: bool = False):
        """set intensity of the UV light: 0 or 50 to 100"""
        # Fixme: ideally the state (heated or not) of the reactor is kept as instance variable so that the light
        #  intensity can be changed without affecting the heating state (i.e. with new default heated=None that keeps
        #  the previous state unchanged
        cmd = self.cmd.SET_UV150.format(power_percent=power, heater_on=int(heated))
        await self.write_and_read_reply(cmd)

    async def trigger_key_press(self, keycode: str):
        """Set valve position."""
        cmd = self.cmd.KEY_PRESS.format(keycode=keycode)
        await self.write_and_read_reply(cmd)

    async def power_on(self):
        """Turn on both devices, R2 and R4."""
        await self.write_and_read_reply(self.cmd.POWER_ON)

    async def power_off(self):
        """Turn off both devices, R2 and R4."""
        await self.write_and_read_reply(self.cmd.POWER_OFF)

    async def get_current_temperature(self, channel=2) -> float | None:
        """Get temperature (in Celsius) from channel3."""
        temp_history = await self.write_and_read_reply(self.cmd.HISTORY_TEMPERATURE)
        if temp_history == "OK":
            logger.warning("ValueError:the reply of get temperature command is OK..")
            return await self.get_current_temperature(channel)

        # 0: time, 1..8: cooling, heating, or ...  / temp (alternating per channel)
        temp_time, *temps = temp_history[0].split(",")
        return float(temps[channel * 2 - 1]) / 10

    async def get_pressure_history(
        self,
    ) -> tuple[int, int, int]:
        """Get pressure history and returns it as (in mbar)"""
        # Get a `&` separated list of pressures for all sensors every second
        pressure_history = await self.write_and_read_reply(self.cmd.HISTORY_PRESSURE)
        if pressure_history == "OK":
            logger.warning("ValueError:the reply for get pressure command is OK....")
            # This may give an infinite loop
            return await self.get_pressure_history()
        # Each pressure data point consists of four values: time and three pressures
        _, *pressures = pressure_history.split("&")[0].split(
            ","
        )  # e.g. 45853,94,193,142
        # Converts to mbar
        p_in_mbar = [int(x) * 10 for x in pressures]
        return p_in_mbar[1], p_in_mbar[2], p_in_mbar[0]  # pumpA, pumpB, system

    async def get_current_pressure(self, pump_code: int = 2) -> int:
        """Get current pressure (in mbar)"""
        press_state_list = await self.get_pressure_history()
        # 0: pump A, 1: pump_B, 2: system pressure
        return press_state_list[pump_code]

    async def get_current_flow(self, pump_code: str) -> float:
        """Get current flow rate (in ul/min)"""
        state = await self.write_and_read_reply(self.cmd.HISTORY_FLOW)
        if state == "OK":
            logger.warning("ValueError:the reply of get flow command is OK....")
            return await self.get_current_flow(pump_code)

        pump_flow = {}
        # _: time, A: pump A, B: pump B
        _, pump_flow["A"], pump_flow["B"] = state.split("&")[0].split(",")
        # 0: time, 1: pump A, 2: pump B
        return float(pump_flow[pump_code])

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
            (
                AllState["pumpA_P"],
                AllState["pumpB_P"],
                AllState["sysP (mbar)"],
            ) = await self.get_pressure_history()
            # AllState["sysP (mbar)"] = await self.get_current_pressure()
            # AllState["pumpA_P"] = await self.get_current_pressure(pump_code = 0)
            # AllState["pumpB_P"] = await self.get_current_pressure(pump_code = 1)
            # AllState["pumpA_flow"] =await self.get_current_flow(pump_code=0)
            # AllState["pumpB_flow"] =await self.get_current_flow(pump_code=1)
            AllState["Temp"] = await self.get_current_temperature()
            # AllState["UVpower"] = await self.get_current_power()
            # self.last_state = parse(self._serial.write_async("sdjskal"))
            # time.sleep(1)
            return AllState

    def components(self):
        list_of_components = [
            R2MainSwitch("Power", self),
            R2GeneralPressureSensor("PressureSensor", self),
            R2GeneralSensor("GSensor2", self),
            UV150PhotoReactor("PhotoReactor", self),
            R2HPLCPump("Pump_A", self, "A"),
            R2HPLCPump("Pump_B", self, "B"),
            R2TwoPortValve("ReagentValve_A", self, 0),
            R2TwoPortValve("ReagentValve_B", self, 1),
            R2TwoPortValve("CollectionValve", self, 4),
            R2InjectionValve("InjectionValve_A", self, 2),
            R2InjectionValve("InjectionValve_B", self, 3),
            R2PumpPressureSensor("PumpSensor_A", self, 0),
            R2PumpPressureSensor("PumpSensor_B", self, 1),
        ]

        # TODO if photoreactor -> REACTOR CHANNEL 1,3 AND 4 + UV150PhotoReactor
        #  if no photoreactor -> REACTOR CHANNEL 1-4 no UV150PhotoReactor

        # Create components for reactor bays
        reactor_temp_limits = {
            ch_num: TempRange(min=ureg.Quantity(t[0]), max=ureg.Quantity(t[1]))
            for ch_num, t in enumerate(zip(self._min_t, self._max_t, strict=True))
        }

        reactors = [
            R4Reactor(f"reactor-{n + 1}", self, n, reactor_temp_limits[n])
            for n in range(4)
        ]
        list_of_components.extend(reactors)

        return list_of_components


if __name__ == "__main__":
    Vapourtec_R2 = R2(port="COM4")

    async def main(Vapourtec_R2):
        """test function"""
        await Vapourtec_R2.initialize()
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
        while True:
            # await pA.infuse("10 ul/min")
            print(f"{await Vapourtec_R2.pooling()}")

            # print(f"current pressure of pump A is {await sA.read_pressure()}")

            # print(f"{await Vapourtec_R2.get_valve_Position(2)}")
            # print(f"Injection valve A {await ivA.get_position()}")
            # await ivA.set_position("inject")
            # await asyncio.sleep(0.5)
            # print(f"Injection valve A {await ivA.get_position()}")
        await r2swich.power_off()

    asyncio.run(main(Vapourtec_R2))
