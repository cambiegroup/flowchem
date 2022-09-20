from __future__ import annotations

from typing import Optional

from flowchem.models.base_device import BaseDevice
from flowchem.units import flowchem_ureg


class Sensor(BaseDevice):
    """
    A generic sensor.

    Attributes:
    - `name`: The name of the Sensor.
    - `rate`: Data collection rate in Hz as a `pint.Quantity`. A rate of 0 Hz corresponds to the sensor being off.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self.rate = flowchem_ureg.parse_expression("0 Hz")
        self._unit: str = ""
        self._base_state = {"rate": "0 Hz"}

    async def _read(self):
        """
        Collects the data.

        In the generic `Sensor` implementation, this raises a `NotImplementedError`.
        Subclasses of `Sensor` should implement their own version of this method.git
        """
        raise NotImplementedError
