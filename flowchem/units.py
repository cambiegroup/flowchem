""" Unit-conversion related functions """
import os
import warnings
from typing import Union, Optional

import pint

# Unit converter, see pint docs for info
from pint import DimensionalityError

# Custom type

AnyQuantity = Union[pint.Quantity, str, float, int]

flowchem_ureg = pint.UnitRegistry()
flowchem_ureg.autoconvert_offset_to_baseunit = True

UNIT_REGISTER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "units.txt")
flowchem_ureg.load_definitions(UNIT_REGISTER)


def ensure_quantity(
    value: AnyQuantity, target: str = "ml", assumed_unit: Optional[str] = None
) -> pint.Quantity:
    """Convert almost any unit into the target unit

    If dimensionless values are provided, units=target are assumed if no assumed_unit is provided.
    """

    if assumed_unit is None:
        assumed_unit = target

    # If it is a string, likely with units...
    if isinstance(value, str):
        parsed_value = pint.Quantity(value)

        # If not unit cast it back to number and it will be treated as such
        if parsed_value.dimensionless:
            parsed_value *= flowchem_ureg.Quantity(assumed_unit)
    elif isinstance(value, pint.Quantity):
        parsed_value = value
    else:
        parsed_value = value * flowchem_ureg.Quantity(assumed_unit)

    try:
        return parsed_value.to(target)
    except DimensionalityError:
        warnings.warn(
            f"Dimensionality error in the conversion of {value} to {target}! Incompatible units?\n"
            f"Assuming {parsed_value.magnitude}{target} was intended..."
        )
        return parsed_value.magnitude * flowchem_ureg.Quantity(target)
