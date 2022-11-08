"""Distribution valves, generally connected to syringe pumps, direct the flow from a fixed port to one of the others."""
from loguru import logger

from flowchem.components.valves.base_valve import BaseValve
from flowchem.devices.flowchem_device import FlowchemDevice


class TwoPortDistribution(BaseValve):
    def __init__(self, name: str, hw_device: FlowchemDevice):
        # These are hardware-port, only input and output are routable from the fixed syringe.
        # All three are listed as this simplifies the creation of graphs
        positions = ["pump", "input", "output"]
        super().__init__(name, hw_device, positions)

    async def set_position(self, position: str) -> bool:
        if position not in self._positions or position == "pump":
            logger.error(f"Invalid position {position} for valve {self.name}!")
            return False
        return True
