# Pump Azura Compact (P 2.1S)
## Introduction
The Knauer Azura Compact pumps can be controlled via flowchem.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an
openAPI endpoint.


## Connection
Knauer pumps are originally designed to be used with HPLC instruments, so they support ethernet communication.
Moreover, they feature an autodiscover mechanism that makes it possible to automatically find the device IP address
of a device given its (immutable) MAC address.
This enables the use of the valves with dynamic addresses (i.e. with a DHCP server) which simplify the setup procedure.

## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-knauer-pump]  # This is the pump identifier
type = "AzuraCompactPump"
ip_address = "192.168.2.1"  # Onyl one of either ip_address or mac_address need to be provided
mac_address = "00:11:22:33:44:55"  #  Onyl one of either ip_address or mac_address need to be provided
max_pressure = "10 bar"  # Optionally, a string with natural language specifying max pressure can be provided
min_pressure = "5 bar"  # Optionally, a string with natural language specifying max pressure can be provided
```

## API methods
Once configured, a flowchem AzuraCompactPump object will expose the following commands:

```{eval-rst}
.. include:: api-pump.rst
```

## Device detection
Azura Compact pumps can be auto-detected via the `flowchem-autodiscover` command-line utility.
After having installed flowchem, run `flowchem-autodiscover` to create a configuration stub with all the devices that
can be auto-detected on your PC.

## Further information
For further information please refer to the [manufacturer manual](./pump_p2.1s_instructions.pdf)
