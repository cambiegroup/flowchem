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
port = 13000  # Default spinsolve port
sample_name = "automated-experiment"
solvent = "chloroform-d"
data_folder = "D:\\data2q\\my-experiment"
remote_to_local_mapping = ["D:\\data2q", "\\BSMC-7WP43Y1\\data2q"]
```
## Remote control
When controlling a Spinsolve instance running on a remote PC, it is necessary that the FIDs are saved in a folder that
is accessible from the PC running flowchem as the Spinsolve API does not natively allow for file transfer.
If network drive are used, a location with the same name can be used on both PC.
If that is not the case, a `remote_to_local_mapping` parameter can be used to translate the remote file hierarchy to the
local (flowchem-accessible) one.
Incidentally, this enables the file sharing across PC with different operative system, e.g. if flowchem is running on linux.
