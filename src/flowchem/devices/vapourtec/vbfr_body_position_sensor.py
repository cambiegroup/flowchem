from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from flowchem.components.pumps.hplc_pump import HPLCPump
from flowchem.components.sensors.sensor import Sensor
from flowchem.components.sensors.body_position_seneor import BodySensor
from flowchem.components.technical.photo import Photoreactor
from flowchem.components.technical.power import PowerSwitch
from flowchem.components.technical.temperature import TemperatureControl, TempRange
from flowchem.components.valves.distribution_valves import TwoPortDistributionValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve

if TYPE_CHECKING:
    from .vbfr_compression_controller import VBFRController


class vbfrBodySensor(BodySensor):
    hw_device: VBFRController

    def __init__(self, name: str, hw_device: VBFRController) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/read-position", self.read_position, methods=["GET"])
        self.add_api_route("/get-run-state", self.get_run_state, methods=["GET"])
        self.add_api_route(
            "/set-system-max-pressure",
            self.set_sys_pressure_limit,
            methods=["PUT"],
        )

    async def read_position(self) -> float:
        """Read body position."""
        return await self.hw_device.get_position()


    async def set_column_size(self, inner_diameter: str = "6.6 mm"):
        return await self.hw_device.set_column_size(inner_diameter)

    async def set_pressure_difference(self, pressure: str) -> bool:
        await self.hw_device.set_pressure_difference(pressure)
        return True