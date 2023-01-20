from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.devices.flowchem_device import FlowchemDevice
from ...components.technical.power import PowerSwitch

if TYPE_CHECKING:
    from .bubble_sensor import PhidgetBubbleSensor, PhidgetPowerSource5V

from flowchem.components.sensors.base_sensor import Sensor


class PhidgetBubbleSensorComponent(Sensor):
    hw_device: PhidgetBubbleSensor  # just for typing

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/set-dataIn", self.power_on, methods=["PUT"])
        self.add_api_route("/read-intensity", self.read_intensity, methods=["GET"])

    async def power_on(self):
        self.hw_device.power_on()

    async def power_off(self):
        self.hw_device.power_off()

    async def read_intensity(self) -> float:
        """Read from sensor, result to be expressed in percentage(%)"""
        return self.hw_device.read_intensity()

    async def set_dataInterval(self, datainterval: int):
        """set data interval at the range 20-60000 ms"""
        self.hw_device.set_dataInterval(datainterval)


class PhidgetBubbleSensorPowerComponent(PowerSwitch):
    hw_device: PhidgetPowerSource5V  # just for typing

    async def power_on(self):
        self.hw_device.power_on()

    async def power_off(self):
        self.hw_device.power_off()
