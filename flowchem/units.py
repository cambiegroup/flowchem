""" Unit-conversion related functions """
from typing import Union

import pint

# Unit converter, see pint docs for info
flowchem_ureg = pint.UnitRegistry()


def value_to_ul_min(value: Union[pint.Quantity, str, float]) -> pint.Quantity:
    """ Convert almost any unit into ul/min """
    # If it is a string, likely with units...
    if isinstance(value, str):
        value = pint.Quantity(value)
        # If not unit cast it back to number and it will be treated as such
        if value.dimensionless:
            value *= flowchem_ureg.ul / flowchem_ureg.min
    # If it is a number assume the right units
    if not isinstance(value, pint.Quantity):
        value *= flowchem_ureg.ul / flowchem_ureg.min

    return value.to("ul/min")


def value_to_bar(value: Union[pint.Quantity, str, float]) -> pint.Quantity:
    """ Convert almost any unit into bar """
    # If it is a string, likely with units...
    if isinstance(value, str):
        value = pint.Quantity(value)
        # If not unit cast it back to number and it will be treated as such
        if value.dimensionless:
            value *= flowchem_ureg.bar
    # If it is a number assume the right units
    if not isinstance(value, pint.Quantity):
        value *= flowchem_ureg.bar

    return value.to("bar")
