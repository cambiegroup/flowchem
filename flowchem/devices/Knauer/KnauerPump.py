"""
Knauer pump control.
"""
import asyncio
import logging
import warnings
from enum import Enum

from flowchem.constants import DeviceError
from flowchem.devices.Knauer.Knauer_common import KnauerEthernetDevice


FLOW = "FLOW"  # 0-50000 µL/min, int only!
PMIN10 = "PMIN10"  # 0-400 in 0.1 MPa, use to avoid dryrunning
PMIN50 = "PMIN50"  # 0-150 in 0.1 MPa, use to avoid dryrunning
PMAX10 = "PMAX10"  # 0-400 in 0.1 MPa, chosen automatically by selecting pump head
PMAX50 = "PMAX50"  # 0-150 in 0.1 MPa, chosen automatically by selecting pumphead
IMIN10 = "IMIN10"  # 0-100 minimum motor current
IMIN50 = "IMIN50"  # 0-100 minimum motor current
HEADTYPE = "HEADTYPE"  # 10, 50 ml. Value refers to highest flowrate in ml/min
STARTLEVEL = "STARTLEVEL"  # 0, 1 configures start. 0 -> only start pump when shorted to GND, 1 -> always allow start
ERRIO = "ERRIO"  # 0, 1 write/read error in/output ??? sets errio either 1 or 0, reports errio:ok
STARTMODE = "STARTMODE"  # 0, 1; 0=pause pump after switchon, 1=start immediatley with previous set flow rate
ADJ10 = "ADJ10"  # 100-2000
ADJ50 = "ADJ50"  # 100-2000
CORR10 = "CORR10"  # 0-300
CORR50 = "CORR50"  # 0-300
EXTFLOW = "EXTFLOW?"
IMOTOR = "IMOTOR?"  # motor current in relative units 0-100
PRESSURE = "PRESSURE?"  # reads the pressure in 0.1 MPa
ERRORS = "ERRORS?"  # displays last 5 error codes
EXTCONTR = (
    "EXTCONTR:"  # 0, 1; 1= allows flow control via external analog input, 0 dont allow
)
LOCAL = "LOCAL"  # no parameter, releases pump to manual control
REMOTE = "REMOTE"  # manual param input prevented
PUMP_ON = "ON"  # starts flow
PUMP_OFF = "OFF"  # stops flow


class KnauerPumpHeads(Enum):
    """
    Two Pumpheads exist, 50 mL/min and 10 mL/min
    """

    FLOWRATE_FIFTY_ML = 50
    FLOWRATE_TEN_ML = 10


class KnauerPump(KnauerEthernetDevice):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.eol = b"\n\r"
        self.max_pressure, self.max_flow = None, None

    async def initialize(self):
        """ Initialize connection """
        # Here the magic happens...
        await super().initialize()

        # Here it is checked that the device is a pump and not a valve
        await self.get_headtype()

    @staticmethod
    def error_present(reply: str) -> bool:
        """ True if there are errors, False otherwise. Warns for errors. """

        if not reply.startswith("ERROR"):
            return False

        if "ERROR:1" in reply:
            warnings.warn(f"Invalid message sent to device.\n")

        elif "ERROR:2" in reply:
            warnings.warn(f"Setpoint refused by device.\n"
                          f"Refer to manual for allowed values.\n")
        else:
            warnings.warn("Unspecified error detected!")
        return True

    async def _communicate(self, message: str) -> str:
        """
        sends command and receives reply, deals with all communication based stuff and checks
        that the valve is of expected type
        :param message:
        :return: reply: str
        """
        reply = await self._send_and_receive(message)
        if self.error_present(reply):
            return ""

        # Setpoint ok
        elif ":OK" in reply:
            logging.info("setpoint successfully set!")
            return "OK"

        # Replies to 'VALUE?' are in the format 'VALUE:'
        elif message[:-1] + ":" in reply:
            logging.info(f"setpoint successfully acquired, value={reply}")
            # Last value after colon
            return reply.split(":")[-1]

        # No reply
        elif not reply:
            warnings.warn("No reply received")
            return ""

        warnings.warn(f"Unrecognized reply: {reply}")
        return reply

    # read and write. write: append ":value", read: append "?"
    async def message_constructor_dispatcher(
        self, message, setpoint: int = None, setpoint_range: tuple = None
    ):
        """
        Create and sends a message from the command.

        If setpoint is given, then the command is appended with :value
        If not setpoint is given, a "?" is added for getter syntax

        e.g. message = "HEADTYPE"
        no setpoint -> sends "HEADTYPE?"
        w/ setpoint -> sends "HEADTYPE:<setpoint_value>"
        """

        # GETTER
        if not setpoint:
            return await self._communicate(message + "?")

        # SETTER with range
        if setpoint_range:
            if setpoint in range(*setpoint_range):
                return await self._communicate(message + ":" + str(setpoint))

            warnings.warn(f"The setpoint provided {setpoint} is not valid for the command "
                          f"{message}!\n Accepted range is: {setpoint_range}.\n"
                          f"Command ignored")
            return ""

        # SETTER w/o range
        else:
            return await self._communicate(message + ":" + str(setpoint))

    async def get_headtype(self):
        head_type_id = await self.message_constructor_dispatcher(HEADTYPE)
        try:
            headtype = KnauerPumpHeads(int(head_type_id))
        except ValueError as e:
            raise DeviceError(
                "It seems you're trying instantiate an unknown device/unknown pump type as Knauer Pump."
                "Only Knauer Azura Compact is supported"
            ) from e
        logging.info(f"Head type of pump {self.ip_address} is {headtype}")

        if headtype == KnauerPumpHeads.FLOWRATE_TEN_ML:
            self.max_pressure, self.max_flow = 400, 10000
        elif headtype == KnauerPumpHeads.FLOWRATE_FIFTY_ML:
            self.max_pressure, self.max_flow = 150, 50000

        return headtype

    async def set_headtype(self, head_type: KnauerPumpHeads):
        await self.message_constructor_dispatcher(HEADTYPE, setpoint=head_type.value)

        self.max_pressure, self.max_flow = (
            (400, 10000)
            if head_type == KnauerPumpHeads.FLOWRATE_TEN_ML
            else (150, 50000)
        )
        logging.info(f"Head type set to {head_type}")

    def set_flow(self, setpoint_in_ml_min: float = None):
        """

        :param setpoint_in_ml_min: in mL/min
        :return: nothing
        """
        set_flowrate_ul_min = int(setpoint_in_ml_min * 1000)
        flow = self.message_constructor_dispatcher(
            FLOW,
            setpoint=set_flowrate_ul_min,
            setpoint_range=(0, self.max_flow + 1),
        )
        logging.info(
            f"Flow of pump {self.ip_address} is set to {setpoint_in_ml_min}, returns {flow}"
        )

    def set_minimum_pressure(self, pressure_in_bar=None):

        command = PMIN10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMIN50

        reply = self.message_constructor_dispatcher(
            command,
            setpoint=pressure_in_bar,
            setpoint_range=(0, self.max_pressure + 1),
        )

        logging.info(
            f"Minimum pressure of pump {self.ip_address} is set to {pressure_in_bar}, returns {reply}"
        )

    def set_maximum_pressure(self, pressure_in_bar=None):
        command = PMAX10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMAX50

        reply = self.message_constructor_dispatcher(
            command,
            setpoint=pressure_in_bar,
            setpoint_range=(0, self.max_pressure + 1),
        )

        logging.info(
            f"Maximum pressure of pump {self.ip_address} is set to {pressure_in_bar}, returns {reply}"
        )

    def set_minimum_motor_current(self, setpoint=None):
        command = IMIN10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else IMIN50

        reply = self.message_constructor_dispatcher(
            command, setpoint=setpoint, setpoint_range=(0, 101)
        )
        logging.info(
            f"Minimum motor current of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_start_level(self, setpoint=None):
        reply = self.message_constructor_dispatcher(
            STARTLEVEL, setpoint=setpoint, setpoint_range=(0, 2)
        )
        logging.info(
            f"Start level of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_start_mode(self, setpoint=None):
        """

        :param setpoint: 0 pause pump after switch on. 1 switch on immediately with previously selected flow rate
        :return: device message
        """
        if setpoint in (0, 1):
            reply = self.message_constructor_dispatcher(STARTMODE, setpoint=setpoint)
            logging.info(
                f"Start mode of pump {self.ip_address} is set to {setpoint}, returns {reply}"
            )
        else:
            logging.warning("Supply binary value")

    def set_adjusting_factor(self, setpoint: int = None):
        command = ADJ10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = self.message_constructor_dispatcher(
            command, setpoint=setpoint, setpoint_range=(0, 2001)
        )
        logging.info(
            f"Adjusting factor of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_correction_factor(self, setpoint=None):
        command = CORR10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else CORR50
        reply = self.message_constructor_dispatcher(
            command, setpoint=setpoint, setpoint_range=(0, 301)
        )
        logging.info(
            f"Correction factor of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    # read only
    def read_pressure(self):
        reply = int(self._communicate(PRESSURE))
        logging.info(f"Pressure reading of pump {self.ip_address} returns {reply} bar")
        return reply

    def read_extflow(self):
        reply = int(self._communicate(EXTFLOW))
        logging.info(f"Extflow reading of pump {self.ip_address} returns {reply}")
        return reply

    def read_errors(self):
        reply = self._communicate(ERRORS)
        logging.info(f"Error reading of pump {self.ip_address} returns {reply}")
        return reply

    def read_motor_current(self):
        reply = int(self._communicate(IMOTOR))
        logging.info(f"Motor current reading of pump {self.ip_address} returns {reply} A")
        return reply

    # TODO run flag
    # write only
    def start_flow(self):
        self._communicate(PUMP_ON)
        logging.info("Pump switched on")

    def stop_flow(self):
        self._communicate(PUMP_OFF)
        logging.info("Pump switched off")

    def set_local(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set local {param}")
            self._communicate(LOCAL + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def set_remote(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set remote {param}")
            self._communicate(REMOTE + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    # no idea what this exactly does...
    def set_errio(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set errio {param}")
            self._communicate(ERRIO + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def set_extcontrol(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set extcontrol {param}")
            self._communicate(EXTCONTR + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def close_connection(self):
        self.sock.close()
        logging.info(f"Connection with {self.ip_address} closed")


if __name__ == '__main__':
    # This is a bug of asyncio on Windows :|
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    p = KnauerPump(ip_address="192.168.1.126")

    async def main(pump: KnauerPump):
        await pump.initialize()
        await pump.set_headtype(head_type=KnauerPumpHeads.FLOWRATE_FIFTY_ML)
        X =await pump.get_headtype()
        print(X)
        await pump.set_headtype(head_type=KnauerPumpHeads.FLOWRATE_TEN_ML)
        Y= await pump.get_headtype()
        print(Y)
    asyncio.run(main(p))