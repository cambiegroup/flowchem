from flowchem.devices.list_known_device_type import autodiscover_device_classes


def test_device_finder():
    device_types = [
        "AzuraCompact",
        "Clarity",
        "Elite11",
        "FakeDevice",
        "HuberChiller",
        "IcIR",
        "KnauerValve",
        "ML600",
        "MansonPowerSupply",
        "PhidgetPressureSensor",
        "ViciValve",
    ]
    found_device_types = autodiscover_device_classes().keys()
    for device_name in device_types:
        assert device_name in found_device_types
