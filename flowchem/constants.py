from pint import UnitRegistry

flowchem_ureg = UnitRegistry()  # Unit converter, defaults are fine, but it would be wise explicitly list the units needed


class DeviceError(BaseException):
    """ Generic DeviceError """
    pass


class InvalidConfiguration(DeviceError):
    """ The configuration provided is not valid, e.g. no connection w/ device obtained """
    pass
