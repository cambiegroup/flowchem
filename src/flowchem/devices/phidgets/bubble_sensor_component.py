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
        self.add_api_route("/set-data-Interval", self.power_on, methods=["PUT"])
        self.add_api_route("/read-voltage", self.read_voltage, methods=["GET"])
        self.add_api_route("/acquire-signal", self.acquire_signal, methods=["GET"])

    async def power_on(self) -> bool:
        self.hw_device.power_on()
        return True

    async def power_off(self) -> bool:
        self.hw_device.power_off()
        return True

    async def read_voltage(self) -> float:
        """Read from sensor in Volt"""
        return self.hw_device.read_voltage()

    async def acquire_signal(self) -> float:
        """transform the voltage from sensor to be expressed in percentage(%)"""
        return self.hw_device.read_intensity()

    async def set_dataInterval(self, datainterval: int) -> bool:
        """set data interval at the range 20-60000 ms"""
        self.hw_device.set_dataInterval(datainterval)
        return True


class PhidgetBubbleSensorPowerComponent(PowerSwitch):
    hw_device: PhidgetPowerSource5V  # just for typing

    async def power_on(self) -> bool:
        self.hw_device.power_on()
        return True

    async def power_off(self) -> bool:
        self.hw_device.power_off()
        return True
