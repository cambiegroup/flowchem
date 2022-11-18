# Single-sourcing version, Option 5 in https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

import pint

# Unit registry
ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
ureg.define("step = []")
ureg.define("stroke = 48000 * step")
