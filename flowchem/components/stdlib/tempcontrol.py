from typing import Optional

from flowchem.units import flowchem_ureg
from flowchem.components.stdlib import ActiveComponent
from flowchem.components.stdlib import Tube


class TempControl(ActiveComponent):
    """
    A generic temperature controller.

    Arguments:
    - `internal_tubing`: The `Tube` inside the temperature controller.
    - `name`: The component's name.

    Attributes:
    - `active`: Whether the temperature controller is active.
    - `internal_tubing`: The `Tube` inside the temperature controller.
    - `name`: The name of the Sensor.
    - `temp`: The temperature setting as a `pint.Quantity`.
    """

    def __init__(self, internal_tubing: Tube, name: Optional[str] = None):
        super().__init__(name=name)
        if not isinstance(internal_tubing, Tube):
            raise TypeError("TempControl must have internal_tubing of type Tube.")
        self.temp = flowchem_ureg.parse_expression("0 degC")
        self.active = False

        self._base_state = dict(temp="0 degC", active=False)
