"""Pressure sensor."""
from .base_sensor import Sensor
from flowchem.devices.flowchem_device import FlowchemDevice


class PhotoSensor(Sensor):
    """A photo sensor."""

    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/power_on", self.power_on, methods=["PUT"])
        self.add_api_route("/power_off", self.power_off, methods=["PUT"])
        self.add_api_route("/read-intensity", self.read_intensity, methods=["GET"])

    async def read_intensity(self):
        """Read from sensor, result to be expressed in % (optional)."""
        ...

    async def power_on(self):
        ...

    async def power_off(self):
        ...
