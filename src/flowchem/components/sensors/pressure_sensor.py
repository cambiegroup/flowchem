"""Pressure sensor."""
from .sensor import Sensor
from flowchem.devices.flowchem_device import FlowchemDevice


class PressureSensor(Sensor):
    """A pressure sensor."""

    def __int__(self, name: str, hw_device: FlowchemDevice):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/read-pressure", self.read_pressure, methods=["GET"])

        # Ontology: Pressure Sensor Device
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/NCIT_C50167"

    async def read_pressure(self, units: str = "bar"):
        """Read from sensor, result to be expressed in units (optional)."""
        ...
