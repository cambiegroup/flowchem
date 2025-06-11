from flowchem.devices.list_known_device_type import autodiscover_device_classes


def test_device_finder():
    device_types = {
        "AzuraCompact",
        "CVC3000",
        "Clarity",
        "EPC",
        "Elite11",
        "FakeDevice",
        "HuberChiller",
        "IcIR",
        "KnauerDAD",
        "KnauerValve",
        "KnauerAutosampler",
        "MFC",
        "ML600",
        "MansonPowerSupply",
        "PhidgetBubbleSensor",
        "PhidgetPowerSource5V",
        "PhidgetPressureSensor",
        "PeltierCooler",
        "R2",
        "R4Heater",
        "Spinsolve",
        "ViciValve",
    }

    dev_found = autodiscover_device_classes()
    assert set(dev_found.keys()) == set(device_types)

    # Check all devices implement base API
    for name, device in dev_found.items():
        if name == "KnauerDADCommands":
            continue  # not a real device

        assert hasattr(device, "initialize")
        assert hasattr(device, "repeated_task")
