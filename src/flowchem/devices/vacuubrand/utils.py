from enum import IntEnum
from pydantic import BaseModel


class PumpControlMode(IntEnum):
    VacuuLAN = 0
    PUMP_DOWN = 1
    VAC_CONTROL = 2
    AUTO = 3
    PROGRAM = 4
    GAUGE = 4


class PumpState(IntEnum):
    OFF = 0
    PUMP_DOWN = 1
    VACUUM_REACHED = 2
    AUTO_OFF = 3  # Below set value


class ProcessStatus(BaseModel):
    is_pump_on: bool
    is_inline_valve_open: bool
    is_coolant_valve_open: bool
    is_venting_valve_open: bool
    control: PumpControlMode
    state: PumpState

    @classmethod
    def from_reply(cls, reply):
        reply_dict = {
            "is_pump_on": bool(int(reply[0])),
            "is_inline_valve_open": bool(int(reply[1])),
            "is_coolant_valve_open": bool(int(reply[2])),
            "is_venting_valve_open": bool(int(reply[3])),
            "control": PumpControlMode(int(reply[4])),
            "state": PumpState(int(reply[5])),
        }
        return cls.parse_obj(reply_dict)
