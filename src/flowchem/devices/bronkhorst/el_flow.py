"""Bronkhorst El-flow mass flow controller (MFC) device driver."""
import asyncio

# Manufacturer package, see https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html.
import propar
from loguru import logger

from flowchem import ureg
from flowchem.devices.bronkhorst.el_flow_component import EPCComponent, MFCComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import wei_hsin


class ProparDevice(FlowchemDevice):
    """Common functions for all propar devices (i.e. EPC and MFC)."""

    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
    ) -> None:
        super().__init__(name)

        # Metadata
        self.device_info.authors = [wei_hsin]
        self.device_info.manufacturer = "Bronkhorst"

        try:
            self.device = propar.instrument(port, address, channel)
        except OSError as e:
            raise ConnectionError(f"Error connecting to {port} -- {e}") from e

        self.id = self.device.id()
        self.wink = self.device.wink
        logger.debug(f"Connected to {self.id} on port {port}")


class EPC(ProparDevice):
    """Electronic Pressure Controller (EPC), mostly used as backpressure regulator (BPR)."""

    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
        max_pressure: float = 10,  # bar = 100 % = 32000
    ) -> None:
        super().__init__(port, name, channel, address)
        self.max_pressure = max_pressure

        # Metadata
        self.device_info.model = "EL-PRESS"

    async def initialize(self):
        """Initialize device."""
        await self.set_pressure("0 bar")
        self.components.append(EPCComponent("EPC", self))

    async def set_pressure(self, pressure: str):
        """Set the setpoint of the instrument (0-32000 = 0-max pressure = 0-100%)."""
        if pressure.isnumeric():
            pressure = pressure + "bar"
            logger.warning("No units provided to set_pressure, assuming bar.")
        set_p = ureg.Quantity(pressure)
        set_n = round(set_p.m_as("bar") * 32000 / self.max_pressure)
        if set_n > 32000:
            self.device.setpoint = 32000
            logger.debug(
                "setting higher than maximum flow rate! set the flow rate to 100%",
            )
        else:
            self.device.setpoint = set_n
            logger.debug(f"set the pressure to {set_n / 320}%")

    async def get_pressure(self) -> float:
        """Get current flow rate in ml/min."""
        m_num = float(self.device.measure)
        return m_num / 32000 * self.max_pressure

    async def get_pressure_percentage(self) -> float:
        """Get current flow rate in percentage."""
        m_num = float(self.device.measure)
        return m_num / 320


class MFC(ProparDevice):
    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
        max_flow: float = 9,  # ml / min = 100 % = 32000
    ) -> None:
        super().__init__(port, name, channel, address)
        self.max_flow = max_flow

        # Metadata
        self.device_info.model = "EL-FLOW"

    async def initialize(self):
        """Ensure connection."""
        await self.set_flow_setpoint("0 ul/min")
        self.components.append(
            MFCComponent("MFC", self),
        )

    async def set_flow_setpoint(self, flowrate: str):
        """Set the setpoint of the instrument (0-32000 = 0-max flowrate = 0-100%)."""
        if flowrate.isnumeric():
            flowrate = flowrate + "ml/min"
            logger.warning(
                "No units provided to set_temperature, assuming milliliter/minutes.",
            )
        set_f = ureg.Quantity(flowrate)
        set_n = round(set_f.m_as("ml/min") * 32000 / self.max_flow)
        if set_n > 32000:
            self.device.setpoint = 32000
            logger.debug(
                "setting higher than maximum flow rate! set the flow rate to 100%",
            )
        else:
            self.device.setpoint = set_n
            logger.debug(f"set the flow rate to {set_n / 320}%")

    async def get_flow_setpoint(self) -> float:
        """Get current flow rate in ml/min."""
        m_num = float(self.device.measure)
        return m_num / 32000 * self.max_flow

    async def get_flow_percentage(self) -> float:
        """Get current flow rate in percentage."""
        m_num = float(self.device.measure)
        return m_num / 320


async def gas_flow(port: str, target_flowrate: str, reaction_time: float):
    Oxygen_flow = MFC(port, max_flow=9)
    await Oxygen_flow.initialize()
    await Oxygen_flow.set_flow_setpoint("900 ul/min")  # 10%
    # await asyncio.sleep(2)
    # for n in range(100):
    #     print(f"{n} time: {await Oxygen_flow.get_flow_setpoint()}%")
    #
    # # Oxygen_flow.set_flow_setpoint(target_point*32000/9.0)
    # # await asyncio.sleep(reaction_time*60)
    print(Oxygen_flow.id)
    await Oxygen_flow.set_flow_setpoint("0 ml/min")


def find_devices_info(port: str):
    """It is also possible to only create a master.
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

    async def multiple_connect():
        flow = MFC("COM7", address=1, max_flow=10)
        pressure = EPC("COM7", address=2, max_pressure=10)
        O2_flow = MFC("COM7", address=6, max_flow=10)

        print(pressure.id)
        print(flow.id)
        print(O2_flow.id)

    asyncio.run(multiple_connect())

    db = propar.database()
    parameters = db.get_parameters([8, 9, 11, 142])
