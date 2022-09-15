# Huber Chiller
## Introduction
The majority of Huber chillers can be controlled via so-called `PB Commands` over serial communication.
A variety of `PB Commands` are supported in `flowchem`, but some of them may be unavailable on specific models, see the
[manufacturer documentation](./pb_commands_handbook.pdf) for more details.

As for all `flowchem` devices, the virtual instrument can be instantiated via a configuration file that generates an
openAPI endpoint.


## Configuration for API use
Configuration sample showing all possible parameters:

```toml
[device.my-huber-chiller]  # This is the chiller identifier
type = "Elite11InfuseOnly"  # Either Elite11InfuseOnly or Elite11InfuseWithdraw depending on model
port = "COM11"  # This will be /dev/tty* under linux/MacOS
address = 0  # Only needed for daisy-chaining. The address can be set on the pump, see manufacturer manual.
diameter = "4.6 mm"  # Syringe diamater
syringe_volume = "1 ml"  # Syringe volume
baudrate = 115200  # Values between 9,600 and 115,200 can be selected on the pump! (115200 assumed if not specified)
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
(flowchem)  dario@eeepc > /tmp/pycharm_project_420 $ elite11-finder
2022-09-14 15:22:05.793 | INFO     | flowchem.devices.harvardapparatus.Elite11_finder:elite11_finder:17 - Found the following serial port(s): ['/dev/ttyS0']
2022-09-14 15:22:05.793 | INFO     | flowchem.devices.harvardapparatus.Elite11_finder:elite11_finder:23 - Looking for pump on /dev/ttyS0...
2022-09-14 15:22:05.793 | ERROR    | flowchem.devices.harvardapparatus.Elite11:__init__:103 - Cannot connect to the Pump on the port </dev/ttyS0>
2022-09-14 15:22:05.793 | ERROR    | flowchem.devices.harvardapparatus.Elite11_finder:main:47 - No Elite11 pump found
```

## Further information
For further information about connection of the pump to the controlling PC, daisy-chaining via firmware cables etc.
please refer to the [manufacturer manual](./11%20Elite%20&%2011%20Elite%20Pico%20Manual%20-%20Rev%20C.pdf).

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* baudrate 9600
* parity even
* stopbits 1
* bytesize 7
```
