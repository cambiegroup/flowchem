# Knauer Valves
## Introduction
A range of different valve heads can be mounted on the same Knauer actuator, so several type of valves can be controlled
with the same protocol. Both standard 6-port-2-position injection valve and multi-position valves
(with 6, 12 or 16 ports) can be controlled via flowchem.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an
openAPI endpoint.


## Connection
Knauer valves are originally designed to be used with HPLC instruments, so they support ethernet communication.
Moreover, they feature an autodiscover mechanism that makes it possible to automatically find the device IP address
of a device given its (immutable) MAC address.
This enables the use of the valves with dynamic addresses (i.e. with a DHCP server) which simplify the setup procedure.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-knauer-valve]  # This is the valve identifier
type = "Knauer6Port2PositionValve"  # Other options are Knauer6Port6PositionValve, Knauer12PortValve and Knauer16PortValve
ip_address = "192.168.2.1"  # Onyl one of either ip_address or mac_address need to be provided
mac_address = "00:11:22:33:44:55"  #  Onyl one of either ip_address or mac_address need to be provided
default_position = "LOAD"  # Valve position to be set upon initialization
```

## Valve positions
The valve position naming follow the general convention of flowchem (see [Base Valve](../../models/valves/base_valvemd):
* Injection valves have position named 'LOAD' and 'INJECT'
* Multiposition valves have positions from '1' to 'n' where n is the total amount of port available.

## Device auto-detection
It is possible to find all the Knauer device in the current local network with the `knauer-finder` utility provided with `flowchem`.
On Windows, you might be asked by Windows Defender to create a rule to allow access to the network.

% FIXME add a successful connection example here :D
```shell
$ knauer-finder
2022-09-15 13:30:40.842 | INFO     | __main__:main:127 - Starting detection
2022-09-15 13:30:42.846 | INFO     | __main__:main:137 - No device found!
```

## Further information
For further information please refer to the [manufacturer manual](./valve_instructions_en.pdf)
