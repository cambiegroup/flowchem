# Manson Laboratory Power Supply

## Introduction
The following models of Manson lab power supply are supported: "HCS-3102", "HCS-3014", "HCS-3204" and "HCS-3202".
Once connected via USB, they are recognized as a virtual serial port and are supported in `flowchem` via the device type `MansonPowerSupply`.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an openAPI endpoint.


## Configuration
Configuration sample showing all possible parameters:

```toml
[device.my-power-supply]  # This is the device name
type = "MansonPowerSupply"
port = "COM12"  # This will be /dev/tty* under linux/MacOS
```

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* baudrate 115200
```


## Device detection
Lab PCs often have several devices connected via serial ports.
A simple command can help you to identify the serial port connected to the Elite11 pump.

Simply run the `elite11-finder` command from the command line, after having installed flowchem.
% FIXME add a successful connection example here :D
```shell
(venv) C:\Users\BS-Flowlab\PycharmProjects\flowchem>elite11-finder
2022-09-20 18:20:25.906 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:17 - Found the following serial port(s): ['COM1', '
COM3', 'COM4']
2022-09-20 18:20:25.912 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:23 - Looking for pump on COM1...
2022-09-20 18:20:26.022 | DEBUG    | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:34 - No pump found on COM1
2022-09-20 18:20:26.041 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:23 - Looking for pump on COM3...
2022-09-20 18:20:26.178 | DEBUG    | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:34 - No pump found on COM3
2022-09-20 18:20:26.211 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:23 - Looking for pump on COM4...
2022-09-20 18:20:26.242 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:29 - Pump found on <COM4>
2022-09-20 18:20:26.400 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:elite11_finder:31 - Pump address is :!
Found a pump with address : on COM4!
2022-09-20 18:20:26.408 | INFO     | flowchem.devices.harvardapparatus.elite11_finder:main:45 - The following serial port are connected to Elite11: {'CO
M4'}
```

## Further information
For further information about connection of the pump to the controlling PC, daisy-chaining via firmware cables etc.
please refer to the [manufacturer manual](./elite11_manual.pdf).
