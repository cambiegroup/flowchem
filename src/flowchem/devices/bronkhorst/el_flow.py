"""
el-flow MFC control by python package bronkhorst-propar
https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html
"""
import propar
import asyncio
from loguru import logger
from typing import Optional

from flowchem import ureg
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.utils.people import *
from .el_flow_component import MFCComponent
class MFC(FlowchemDevice):
    DEFAULT_CONFIG ={"address" :0x80, "baudrate" :38400}

    def __init__(self, port: str, name=""):
        self.port = port
        self.max_flow = 9 #ml / min = 100 % = 32000
        super().__init__(name)


        self.metadata = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="bronkhorst",
            model="MFC",
        )

        try:
            self.el_flow = propar.instrument(self.port)
            logger.debug(f"Connected to {self.port}")
            return
        except OSError as e:
            raise ConnectionError(
                f"Error connecting to {self.port} -- {e}"
            ) from e


    async def set_flow_setpoint(self, flowrate: str):
        """Set the setpoint of the instrument (0-32000 = 0-max flowrate = 0-100%)."""
        if flowrate.isnumeric():
            flowrate = flowrate + "ul/min"
            logger.warning("No units provided to set_temperature, assuming microliter/minutes.")
        set_f = ureg.Quantity(flowrate)
        set_n = round(set_f.m_as("ul/min")*32/self.max_flow)
        self.el_flow.setpoint = set_n
        logger.debug(f"set the flow rate to {set_n/320}%")

    async def measure(self) -> float:
        """Get current flow rate in percentage"""
        m_num = float(self.el_flow.measure)
        return m_num/320

    async def wink(self):
        """Wink the LEDs on the instrument."""
        # default wink 9 time
        self.el_flow.wink()

    async def get_id(self):
        """Reads the ID parameter of the instrument."""
        return self.el_flow.id()

    def components(self):
        """Return a component."""
        return (MFCComponent("el_flow_MFC", self),)

async def gas_flow(target_flowrate: str, reaction_time:float):

    Oxygen_flow = MFC('COM6')
    await Oxygen_flow.set_flow_setpoint("900 ul/min") #10%
    await asyncio.sleep(2)
    for n in range(100):
        print(f"{n} time: { await Oxygen_flow.measure()}%")

    # Oxygen_flow.set_flow_setpoint(target_point*32000/9.0)
    # await asyncio.sleep(reaction_time*60)

    await Oxygen_flow.set_flow_setpoint("0")

if __name__ == "__main__":
    asyncio.run(gas_flow("0.05 ml/min", 25))

