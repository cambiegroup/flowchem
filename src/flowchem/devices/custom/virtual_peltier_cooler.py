from flowchem.components.technical.temperature import TempRange
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.custom.peltier_cooler_component import (
    PeltierCoolerTemperatureControl,
)
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import asyncio
import pint


class VirtualPeltierCooler(FlowchemDevice):

    def __init__(self, name: str = "", *args, **kwargs):

        super().__init__(name)

        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Manufacturer"
        self.device_info.model = "Virtual Peltier Cooler"
        logger.debug("Connected virtual Virtual Peltier Cooler")

        self.current_temperature = 0
        self.power = 0

    async def initialize(self):
        temp_range = TempRange(
            min=ureg.Quantity("0 °C"),
            max=ureg.Quantity("100 °C")
        )
        list_of_components = [
            PeltierCoolerTemperatureControl("temperature_control", self, temp_limits=temp_range)
        ]
        self.components.extend(list_of_components)

    @classmethod
    def from_config(cls, *args, name: str = "", **kwargs):
        logger.info(f"Connected to virtual Peltier Cooler: {name}")
        return cls(name=name)

    async def set_temperature(self, temperature: pint.Quantity):
        """ Override set_temperature to simulate temperature changes. """
        self.current_temperature = temperature.m_as("°C")
        logger.debug(f"Virtual temperature set to {self.current_temperature} °C")
        await asyncio.sleep(0.01)

    async def get_temperature(self) -> float:
        """ Override get_temperature to return the simulated value. """
        return self.current_temperature

    async def get_power(self) -> float:
        """ Override get_power to return a simulated power value. """
        return self.power

    async def start_control(self):
        ...

    async def stop_control(self):
        ...

    async def get_parameters(self) -> str:
        return f"{self.current_temperature},1"
