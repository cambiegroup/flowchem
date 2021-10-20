from pint import UnitRegistry

flowchem_ureg = UnitRegistry()


class InvalidConfiguration(Exception):
    """ The configuration provided is not valid, e.g. no connection w/ device obtained """
    pass
