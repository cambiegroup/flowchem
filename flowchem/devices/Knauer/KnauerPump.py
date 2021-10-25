"""
Knauer pump control.
"""

import logging
from enum import Enum

from constants import DeviceError
from devices.Knauer.KnauerValve import FLOW, PMIN10, PMIN50, PMAX10, PMAX50, IMIN10, IMIN50, HEADTYPE, STARTLEVEL, \
    ERRIO, STARTMODE, ADJ10, ADJ50, CORR10, CORR50, EXTFLOW, IMOTOR, PRESSURE, ERRORS, EXTCONTR, LOCAL, REMOTE, PUMP_ON, \
    PUMP_OFF
from devices.Knauer.Knauer_common import KnauerEthernetDevice


class KnauerPumpHeads(Enum):
    """
    Two Pumpheads exist, 50 mL/min and 10 mL/min
    """

    FLOWRATE_FIFTY_ML = 50
    FLOWRATE_TEN_ML = 10


class KnauerPump(KnauerEthernetDevice):
    def __init__(
        self,
        ip_address,
        port=None,
        buffersize=None,
    ):
        super().__init__(ip_address, port, buffersize)
        self.max_pressure, self.max_flow = None, None
        # Check connection by reading pump head type
        _ = self.headtype

    def communicate(self, message: str):
        """
        sends command and receives reply, deals with all communication based stuff and checks
        that the valve is of expected type
        :param message:
        :return: reply: str
        """

        # beware: I think the pumps want \n\r as end of message, the valves \r\n
        message = str(message) + "\n\r"
        reply = super()._send_and_receive_handler(message).rstrip()
        if "ERROR:1" in reply:
            DeviceError(
                f"Invalid message sent to device. Message was: {message}. Reply is {reply}"
            )

        elif "ERROR:2" in reply:
            DeviceError(
                f"Setpoint refused by device. Refer to manual for allowed values.  Message was: '{message}'. "
                f"Reply is '{reply}'"
            )

        elif ":OK" in reply:
            logging.info("setpoint successfully set")

        elif message.rstrip()[:-1] + ":" in reply:
            logging.info(f"setpoint successfully acquired, is {reply}")
            return reply.split(":")[-1]
        elif not reply:
            raise DeviceError("No reply received")
        return reply

    # read and write. write: append ":value", read: append "?"
    def message_constructor_dispatcher(
        self, message, setpoint: int = None, setpoint_range: tuple = None
    ):

        if not setpoint:
            return self.communicate(message + "?")

        elif setpoint_range:
            if setpoint in range(*setpoint_range):
                return self.communicate(message + ":" + str(setpoint))

            else:
                DeviceError(
                    f"Internal check shows that setpoint provided ({setpoint}) is not in range ({setpoint_range})."
                    f"Refer to manual."
                )

        else:
            return self.communicate(message + ":" + str(setpoint))

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

    @property
    def headtype(self):
        reply = int(self.message_constructor_dispatcher(HEADTYPE)[-2:])
        try:
            headtype = KnauerPumpHeads(reply)
        except ValueError as e:
            raise DeviceError(
                "It seems you're trying instantiate an unknown device/unknown pump type as Knauer Pump."
                "Only Knauer Azura Compact is supported"
            ) from e

        logging.info(f"Head type of pump {self.ip_address} is {headtype}")
        self.max_pressure, self.max_flow = (
            (400, 10000)
            if headtype == KnauerPumpHeads.FLOWRATE_TEN_ML
            else (150, 50000)
        )
        return headtype

    @headtype.setter
    def headtype(self, setpoint: KnauerPumpHeads):
        reply = self.message_constructor_dispatcher(HEADTYPE, setpoint=setpoint.value)
        self.max_pressure, self.max_flow = (
            (400, 10000)
            if setpoint == KnauerPumpHeads.FLOWRATE_TEN_ML
            else (150, 50000)
        )
        logging.info(
            f"Head type of pump {self.ip_address} is set to {setpoint}, returns {reply}"
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
        reply = int(self.communicate(PRESSURE))
        logging.info(f"Pressure reading of pump {self.ip_address} returns {reply} bar")
        return reply

    def read_extflow(self):
        reply = int(self.communicate(EXTFLOW))
        logging.info(f"Extflow reading of pump {self.ip_address} returns {reply}")
        return reply

    def read_errors(self):
        reply = self.communicate(ERRORS)
        logging.info(f"Error reading of pump {self.ip_address} returns {reply}")
        return reply

    def read_motor_current(self):
        reply = int(self.communicate(IMOTOR))
        logging.info(f"Motor current reading of pump {self.ip_address} returns {reply} A")
        return reply

    # TODO run flag
    # write only
    def start_flow(self):
        self.communicate(PUMP_ON)
        logging.info("Pump switched on")

    def stop_flow(self):
        self.communicate(PUMP_OFF)
        logging.info("Pump switched off")

    def set_local(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set local {param}")
            self.communicate(LOCAL + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def set_remote(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set remote {param}")
            self.communicate(REMOTE + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    # no idea what this exactly does...
    def set_errio(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set errio {param}")
            self.communicate(ERRIO + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def set_extcontrol(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set extcontrol {param}")
            self.communicate(EXTCONTR + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def close_connection(self):
        self.sock.close()
        logging.info(f"Connection with {self.ip_address} closed")