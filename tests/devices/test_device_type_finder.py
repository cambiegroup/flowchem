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
    for dev in dev_found:
        if not dev.startswith("Virtual"):
            if dev not in device_types:
                print(f"The device {dev} is not listed in the device_types")

    # Check all devices implement base API
    for name, device in dev_found.items():
        if name.startswith("Virtual"):
            continue  # not a real device

        assert hasattr(device, "initialize")
        assert hasattr(device, "repeated_task")
