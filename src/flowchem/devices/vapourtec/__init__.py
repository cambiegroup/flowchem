""" Vapourtec devices """
try:
    from .r4_heater import R4Heater

    __all__ = ["R4Heater"]
except PermissionError:
    print("Vapourtec devices disabled - no command description found.")
