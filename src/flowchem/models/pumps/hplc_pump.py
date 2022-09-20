from abc import ABC

from flowchem.models.pumps.base_pump import BasePump


class HplcPump(BasePump, ABC):
    """
    A generic HPLC pump.

    Arguments:
    - `name`: The name of the pump.

    Attributes:
    - `name`: The name of the pump.
    - `rate`: The flow rate of the pump as a `pint.Quantity`. Must be of the dimensionality of volume/time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # HPLC isocratic pump
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0000556")
