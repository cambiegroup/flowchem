from flowchem.devices.find_device_type import autodiscover_device_classes


def test_device_finder():
    device_types = [
        "AzuraCompactPump",
        "Elite11InfuseOnly",
        "Elite11InfuseWithdraw",
        "FlowIR",
        "HuberChiller",
        "Knauer12PortValve",
        "Knauer16PortValve",
        "Knauer6Port2PositionValve",
        "Knauer6Port6PositionValve",
        "ML600",
        "MansonPowerSupply",
        "PressureSensor",
        "Spinsolve",
        "ViciValve",
    ]
    found_device_types = autodiscover_device_classes().keys()
    for device_name in device_types:
        assert device_name in found_device_types
