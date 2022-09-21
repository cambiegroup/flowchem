# import all submodules to add them to the flowchem.device namespace
# This is so that users do not need to know inner manufacturer-based folder structure
# Explicit
# from .hamilton import ML600
# from .harvardapparatus import Elite11InfuseOnly, Elite11InfuseWithdraw
# Implicit alternative
import importlib
import pkgutil

for mod_info in pkgutil.walk_packages(__path__, __name__ + "."):
    mod = importlib.import_module(mod_info.name)

    # Emulate `from mod import *`
    try:
        names = mod.__dict__["__all__"]
    except KeyError:
        names = [k for k in mod.__dict__ if not k.startswith("_")]

    globals().update({k: getattr(mod, k) for k in names})
