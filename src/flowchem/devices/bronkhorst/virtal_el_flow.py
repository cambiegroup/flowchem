from flowchem.devices.bronkhorst.el_flow_component import EPCComponent, MFCComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger


def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


class VirtualEPC(FlowchemDevice):

    def __init__(self, name="", *args, max_pressure: float = 10, **kwargs) -> None:

        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "VirtualBronkhorst"
        self.device_info.model = "EPC"
        logger.info("Connected virtual EPC")

        self.pressure = "0 bar"
        self.max_pressure = max_pressure

    async def initialize(self):
        await self.set_pressure("0 bar")
        self.components.append(EPCComponent("EPC", self))

    async def set_pressure(self, pressure: str):
        if pressure.isnumeric() or isfloat(pressure):
            pressure = pressure + "bar"
            logger.warning("No units provided to set_pressure, assuming bar.")
        self.pressure = pressure

    async def get_pressure(self) -> float:
        return ureg.Quantity(self.pressure).magnitude

    async def get_pressure_percentage(self) -> float:
        return 100 * ureg.Quantity(self.pressure).magnitude / self.max_pressure


class VirtualMFC(FlowchemDevice):

    def __init__(self, name="", *args, max_flow: float = 9, **kwargs) -> None:

        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "VirtualBronkhorst"
        self.device_info.model = "EL-FLOW"
        logger.debug("Connected virtual MFC")

        self.max_flow = max_flow
        self.flow = "0 ml/min"

    async def initialize(self):
        await self.set_flow_setpoint("0 ml/min")
        self.components.append(MFCComponent("MFC", self))

    async def set_flow_setpoint(self, flowrate: str):
        if flowrate.isnumeric() or isfloat(flowrate):
            flowrate = flowrate + "ml/min"
            logger.warning(
                "No units provided to set_flow_rate, assuming milliliter/minutes.",
            )
        self.flow = flowrate

    async def get_flow_setpoint(self) -> float:
        return ureg.Quantity(self.flow).magnitude

    async def get_flow_percentage(self) -> float:
        return 100 * ureg.Quantity(self.flow).magnitude / self.max_flow

