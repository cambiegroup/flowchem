from pint import UnitRegistry

flowchem_ureg = UnitRegistry()


class DeviceError(BaseException):
    """ Generic DeviceError """
    pass


class InvalidConfiguration(DeviceError):
    """ The configuration provided is not valid, e.g. no connection w/ device obtained """
    pass

class ActuationError(DeviceError):
    """The attepted move did not succeed"""
    pass
