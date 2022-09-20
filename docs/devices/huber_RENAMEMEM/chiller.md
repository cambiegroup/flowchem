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
type = "HuberChiller"
port = "COM11"  # This will be /dev/tty* under linux/MacOS
```

```{note} Serial connection parameters
Note, further parameters for the serial connections (i.e. those accepted by `serial.Serial`) such as `baudrate`,
`parity`, `stopbits` and `bytesize` can be specified.
However, it should not be necessary as the following values (which are the default for the instrument) are
automatically used:
* baudrate 9600 (with Com.G@te other baud rates are possible)
* parity none
* stopbits 1
* bytesize 8
```

## Device detection
Lab PCs often have several devices connected via serial ports.
A simple command can help you to identify the serial port connected to the Elite11 pump.

Simply run the `huber-chiller-finder` command from the command line, after having installed flowchem.
% FIXME add a successful connection example here :D
```shell
$ huber_chiller_finder.py
2022-09-15 13:07:29.095 | INFO     | __main__:chiller_finder:17 - Found the following serial port(s): ['/dev/ttyS0']
2022-09-15 13:07:29.095 | INFO     | __main__:chiller_finder:23 - Looking for chiller on /dev/ttyS0...
2022-09-15 13:07:29.096 | WARNING  | __main__:chiller_finder:27 - Cannot open /dev/ttyS0!
2022-09-15 13:07:29.096 | ERROR    | __main__:main:49 - No Huber chiller found
```

## Further information
For further information please refer to the [manufacturer manual](./pb_commands_handbook.pdf)

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
