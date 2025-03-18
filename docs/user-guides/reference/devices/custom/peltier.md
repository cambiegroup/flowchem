# Peltier cooler

## Introduction
Control module for Peltier cooler via a TEC05-24 or TEC16-24 controller.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-peltier]  # This is the device name
type = "PeltierCooler"
port = "COM12"  
address = 0  #  
peltier_defaults = "default"  # Optional (default or low_cooling)
```

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`, 
`parity`, `stopbits` and `bytesize` can be specified.
```

## API methods
See the [device API reference](../../api/manson_power_supply/api.md) for a description of the available methods.
