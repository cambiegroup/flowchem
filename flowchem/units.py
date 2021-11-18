""" Unit-conversion related functions """
import os

import pint

flowchem_ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

UNIT_REGISTER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "units.txt")
flowchem_ureg.load_definitions(UNIT_REGISTER)
