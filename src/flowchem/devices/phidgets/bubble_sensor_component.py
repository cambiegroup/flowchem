from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.devices.flowchem_device import FlowchemDevice

if TYPE_CHECKING:
    from .bubble_sensor import PhidgetBubbleSensor, PhidgetBubbleSensor_power
from flowchem.components.sensors.base_sensor import Sensor
from flowchem.components.base_component import FlowchemComponent


class PhidgetBubbleSensorComponent(Sensor):
    hw_device: PhidgetBubbleSensor  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)

    async def read_intensity(self) -> float:
        """Read from sensor, result to be expressed in percentage(%)"""
        return self.hw_device.read_intensity()

    async def power_on(self):
        self.hw_device.power_on()

    async def power_off(self):
        self.hw_device.power_off()

    async def set_dataInterval(self, datainterval: int):
        """set data interval """
        # TODO: check the range
        self.hw_device.set_dataInterval(datainterval)


class PhidgetBubbleSensorPowerComponent(Sensor):
    hw_device: PhidgetBubbleSensor_power  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic power supply"""
        super().__init__(name, hw_device)

    async def power_on(self):
        self.hw_device.power_on()

    async def power_off(self):
        self.hw_device.power_off()
