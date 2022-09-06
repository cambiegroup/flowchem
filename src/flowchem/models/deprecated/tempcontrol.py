from abc import ABC
from typing import Optional

from flowchem.components.properties import ActiveComponent
from flowchem.units import flowchem_ureg


class TempControl(ActiveComponent, ABC):
    """
    A generic temperature controller.

    Arguments:
    - `internal_tubing`: The `Tube` inside the temperature controller.
    - `name`: The component's name.

    Attributes:
    - `active`: Whether the temperature controller is active.
    - `name`: The name of the Sensor.
    - `temp`: The temperature setting as a `pint.Quantity`.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)

        self.temp = flowchem_ureg.parse_expression("0 degC")
        self.active = False

        self._base_state = dict(temp="0 degC", active=False)
