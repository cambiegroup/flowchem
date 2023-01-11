import propar
import asyncio
from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.utils.people import *

class MFC(FlowchemDevice):
    """MFC """

    DEFAULT_CONFIG ={"address" :0x80, "baudrate" :38400}

    def __init__(self, port: str, name =""):
        self.port = port
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


    async def set_flow_setpoint(self, flowrate: int):
        # max_flow = 9 ml/min = 100% = 32000
        self.el_flow.setpoint = flowrate
        logger.debug(f"set the flow rate to {flowrate/320}%")

    async def measure(self) -> int:
        return self.el_flow.measure


async def gas_flow(target_point: float, reaction_time:float):

    Oxygen_flow = MFC('COM6')
    await Oxygen_flow.set_flow_setpoint(3200) #10%
    await asyncio.sleep(2)
    for n in range(100):
        print(f"{n} time: { (await Oxygen_flow.measure() )/ 320}%")

    # Oxygen_flow.set_flow_setpoint(target_point*32000/9.0)
    # await asyncio.sleep(reaction_time*60)

    await Oxygen_flow.set_flow_setpoint(0)

if __name__ == "__main__":
    asyncio.run(gas_flow(0.01, 25))

