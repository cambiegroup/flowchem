"""Unit-conversion related functions."""
import pint

flowchem_ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
flowchem_ureg.define("step = []")
flowchem_ureg.define("stroke = 48000 * step")
