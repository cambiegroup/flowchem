from flowchem.devices.list_known_device_type import autodiscover_device_classes


def test_device_finder():
    device_types = [
        "AzuraCompact",
        "Clarity",
        "Elite11",
        "FakeDevice",
        "HuberChiller",
        "IcIR",
        "KnauerDAD",
        "KnauerValve",
        "ML600",
        "MansonPowerSupply",
        "PhidgetPressureSensor",
        "Spinsolve",
        "ViciValve",
    ]

    dev_found = autodiscover_device_classes()
    # Check all expected devices are there
    for device_name in device_types:
        assert device_name in dev_found.keys()

    # Check all devices implement base API
    for name, device in dev_found.items():
        if name == "KnauerDADCommands":
            continue  # not a real device

        assert hasattr(device, "components")
        assert hasattr(device, "initialize")
