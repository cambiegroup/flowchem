try:
    from .R4_heater import R4Heater
except PermissionError:
    print("Vapourtec components disabled - no command description found.")
