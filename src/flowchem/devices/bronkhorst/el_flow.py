"""
el-flow MFC control by python package bronkhorst-propar
https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html
"""
import propar
import asyncio
from loguru import logger

from flowchem import ureg
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.utils.people import jakob, dario, wei_hsin
from flowchem.devices.bronkhorst.el_flow_component import MFCComponent, EPCComponent


def isfloat(self, num):
    try:
        float(num)
        return True
    except ValueError:
        return False

class EPC(FlowchemDevice):
    DEFAULT_CONFIG = {"channel": 1, "baudrate": 38400}  # "address": 0x80

    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
        max_pressure: float = 10,  # bar = 100 % = 32000
    ):
        self.port = port
        self.channel = channel
        self.address = address
        self.max_pressure = max_pressure
        super().__init__(name)

        self.metadata = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="bronkhorst",
            model="EPC",
        )

        try:
            self.el_press = propar.instrument(
                self.port, address=self.address, channel=self.channel
            )
            self.id = self.el_press.id
            logger.debug(f"Connected {self.id} to {self.port}")
            return
        except OSError as e:
            raise ConnectionError(f"Error connecting to {self.port} -- {e}") from e

    async def initialize(self):
        """Ensure connection."""
        await self.set_pressure("0 bar")


    async def set_pressure(self, pressure: str):
        """Set the setpoint of the instrument (0-32000 = 0-max pressure = 0-100%)."""
        if pressure.isnumeric() or isfloat(pressure):
            pressure = pressure + "bar"
            logger.warning("No units provided to set_pressure, assuming bar.")
        set_p = ureg.Quantity(pressure)
        set_n = round(set_p.m_as("bar") * 32000 / self.max_pressure)
        if set_n > 32000:
            self.el_press.setpoint = 32000
            logger.debug(
                "setting higher than maximum flow rate! set the flow rate to 100%"
            )
        else:
            self.el_press.setpoint = set_n
            logger.debug(f"set the pressure to {set_n / 320}%")

    async def get_pressure(self) -> float:
        """Get current flow rate in ml/min"""
        m_num = float(self.el_press.measure)
        return m_num / 32000 * self.max_pressure

    async def get_pressure_percentage(self) -> float:
        """Get current flow rate in percentage"""
        m_num = float(self.el_press.measure)
        return m_num / 320

    async def wink(self):
        """Wink the LEDs on the instrument."""
        # default wink 9 time
        self.el_press.wink()

    async def get_id(self):
        """Reads the Serial Number (SN) of the instrument."""
        return self.el_press.id

    def components(self):
        """Return a component."""
        return (EPCComponent("el_press_EPC", self),)


class MFC(FlowchemDevice):
    DEFAULT_CONFIG = {"channel": 1, "baudrate": 38400}  # "address": 0x80

    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
        max_flow: float = 9,  # ml / min = 100 % = 32000
    ):
        self.port = port
        self.channel = channel
        self.address = address
        self.max_flow = max_flow
        super().__init__(name)

        self.metadata = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="bronkhorst",
            model="MFC",
        )

        try:
            self.el_flow = propar.instrument(
                self.port, address=self.address, channel=self.channel
            )
            self.id = self.el_flow.id
            logger.debug(f"Connected {self.id} to {self.port}")
            return
        except OSError as e:
            raise ConnectionError(f"Error connecting to {self.port} -- {e}") from e

    async def initialize(self):
        """Ensure connection."""
        await self.set_flow_setpoint("0 ul/min")

    async def set_flow_setpoint(self, flowrate: str):
        """Set the setpoint of the instrument in ml/min (0-32000 = 0-max flowrate = 0-100%)."""
        if flowrate.isnumeric() or isfloat(flowrate):
            flowrate = flowrate + "ml/min"
            logger.warning(
                "No units provided to set_flow_rate, assuming milliliter/minutes."
            )

        set_f = ureg.Quantity(flowrate)
        set_n = round(set_f.m_as("ml/min") * 32000 / self.max_flow)
        if set_n > 32000:
            self.el_flow.setpoint = 32000
            logger.debug(
                "setting higher than maximum flow rate! set the flow rate to 100%"
            )
        else:
            self.el_flow.setpoint = set_n
            logger.debug(f"set the flow rate to {set_n / 320}%")

    async def get_flow_setpoint(self) -> float:
        """Get current flow rate in ml/min"""
        m_num = float(self.el_flow.measure)
        return m_num / 32000 * self.max_flow

    async def get_flow_percentage(self) -> float:
        """Get current flow rate in percentage"""
        m_num = float(self.el_flow.measure)
        return m_num / 320

    async def wink(self):
        """Wink the LEDs on the instrument."""
        # default wink 9 time
        self.el_flow.wink()

    async def get_id(self):
        """Reads the ID parameter of the instrument."""
        return self.el_flow.id

    def components(self):
        """Return a component."""
        return (MFCComponent("el_flow_MFC", self),)


async def gas_flow(port: str, target_flowrate: str, reaction_time: float):
    Oxygen_flow = MFC(port, max_flow=10, address=6)
    await Oxygen_flow.initialize()
    await Oxygen_flow.set_flow_setpoint("900 ul/min")  # 10%
    # await asyncio.sleep(2)
    # for n in range(100):
    #     print(f"{n} time: {await Oxygen_flow.get_flow_setpoint()}%")
    #
    # # Oxygen_flow.set_flow_setpoint(target_point*32000/9.0)
    # # await asyncio.sleep(reaction_time*60)
    O2_flow_id = await Oxygen_flow.get_id()
    print(O2_flow_id)
    await Oxygen_flow.set_flow_setpoint("0 ml/min")


async def mutiple_connect():
    flow = MFC("COM7", address=1, max_flow=10)
    pressure = EPC("COM7", address=2, max_pressure=10)
    O2_flow = MFC("COM7", address=6, max_flow=10)
    # O2_id = O2_flow.get_id
    # print(await pressure.get_id)
    # print(await flow.get_id)
    await flow.set_flow_setpoint("0.5")
    await flow.set_flow_setpoint("0")


def find_devices_info(port: str):
    """
    It is also possible to only create a master.
    This removes some abstraction offered by the instrument class,
    such as the setpoint and measure properties,
    the readParameter and writeParameter functions,
    and having to supply the node number on each read/write parameter call.
    """
    # Create the master
    master = propar.master(port, 38400)

    # Get nodes on the network
    nodes = master.get_nodes()

    # Read the usertag of all nodes
    for node in nodes:
        print(node)
        user_tag = master.read(node["address"], 113, 6, propar.PP_TYPE_STRING)
        print(user_tag)


if __name__ == "__main__":
    # find_devices_info("COM7")
    # asyncio.run(gas_flow("COM7", "0.05 ml/min", 25))
    asyncio.run(mutiple_connect())
    # print(flow.wink())

    db = propar.database()
    parameters = db.get_parameters([8, 9, 11, 142])
