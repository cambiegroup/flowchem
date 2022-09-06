""" HW device, organized by manufacturer. """
from .devices.Hamilton import *
from .devices.Harvard_Apparatus import *
from .devices.Huber import *
from .devices.Knauer import *
from .devices.Magritek import *
from .devices.Manson import *
from .devices.MettlerToledo import *
from .devices.Phidgets import *
from .devices.Vapourtec import *
from .devices.ViciValco import *

# Option 5 in https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
from importlib import metadata
__version__ = metadata.version('flowchem')
