from abc import ABC
from typing import Optional

from flowchem.units import flowchem_ureg
from flowchem.components.properties import ActiveComponent


class Pump(ActiveComponent, ABC):
    """
    A generic pumping device whose primary feature is that it moves fluid.

    Arguments:
    - `name`: The name of the pump.

    Attributes:
    - `name`: The name of the pump.
    - `rate`: The flow rate of the pump as a `pint.Quantity`. Must be of the dimensionality of volume/time.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self.rate = flowchem_ureg.parse_expression("0 ml/min")
        self._base_state = dict(rate="0 mL/min")
