# Magritek Spinsolve
## Introduction
The bench-top NMRs from Magritek are controlled by the proprietary software Spinsolve.
Spinsolve can be controlled remotely via XML over HTTP.

As for all `flowchem` devices, a Spinsolve virtual instrument can be instantiated via a configuration file that generates an openAPI endpoint.
A peculiarity of controlling the NMR in this way is that the FIDs acquired are stored on
the computer where spinsolve is installed, which may or may not be the same PC where flowchem
is running.
Some utility functions are provided in case you are controlling Spinsolve on a different PC than the one running flowchem, see below for more details.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-benchtop-nmr]  # This is the valve identifier
type = "Spinsolve"
host = "127.0.0.1"  # IP address of the PC running Spinsolve, 127.0.0.1 for local machine. Only necessary parameter.
port = 13000
sample_name = "automated-experiment"
solvent = "chloroform-d"
```

## Remote control
An optional parameter `remote_to_local_mapping` can be used to pass a mapping that translates spinsolve PC's path to the
fowchem PC path assuming files are saved on a network drive.
However, currently this is only possible with the programmatic use of Spinsolve object.
