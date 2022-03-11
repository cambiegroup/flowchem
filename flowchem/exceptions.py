""" Exceptions used in the flowchem module. """


class DeviceError(BaseException):
    """Generic DeviceError"""


class InvalidConfiguration(DeviceError):
    """The configuration provided is not valid, e.g. no connection w/ device obtained"""


class ActuationError(DeviceError):
    """The attempted move did not succeed"""


class ProtocolCancelled(Exception):
    """The protocol was cancelled by the user"""
