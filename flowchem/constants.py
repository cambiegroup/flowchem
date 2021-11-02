from pint import UnitRegistry

# necessary/workaround for offset units like celsius, internally these are now converted to  absolute units for arithmetic operations
flowchem_ureg = UnitRegistry(autoconvert_offset_to_baseunit = True)

class DeviceError(BaseException):
    """ Generic DeviceError """
    pass


class InvalidConfiguration(DeviceError):
    """ The configuration provided is not valid, e.g. no connection w/ device obtained """
    pass

class ActuationError(DeviceError):
    """The attepted move did not succeed"""
    pass
