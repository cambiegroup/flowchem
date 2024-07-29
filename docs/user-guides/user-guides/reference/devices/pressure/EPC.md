# Bronkhorst El-Pressure controller

## Introduction

Bronkhorst El-Pressure controller controller (EPC) device driver.

More information about the device can be found in the supplier platform [Bronkhorst](https://www.bronkhorst.com/en-gb/).

## electronic pressure controller



## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-EPC]  # This is the MFC identifier
port = "COM4"    # Access port (serial)
channel = 1      
address = 0x80
max_pressure = 9
```

The class was built base on the package of the 
[manufacturer](https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html).

## API methods
See the [pressure sensor API reference](../../api/bronkhorst_EPC/api.md) for a description of the available methods.
