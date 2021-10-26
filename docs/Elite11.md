Harvard Apparatus Elite 11
==========================

Flowchem implements the Protocol11 syntax to communicate with Elite11 pumps.

## Table of Contents
* [Connection](#connection)
* [Basic usage](#basic usage)
* [Advanced features](#advanced features)
* [API docs](#API docs)

## Connection
The USB type-B port on the back of the pump, once connected to a PC, creates a virtual serial port (drivers are 
auto-installed on Windows and not needed on Linux).

To identify the serial port to which the pump is connected to you can use the utility function `elite11_finder()` as 
follows:

```pycon
>>> from flowchem.devices.Harvard_Apparatus.Elite11_finder import elite11_finder
>>> elite11_finder()
Looking for pump on COM3...
Looking for pump on COM4...
Found a pump with address 06 on COM4!
Out[5]: {'COM4'}

```

 .. note::
Multiple pumps can be daisy chained on the same serial port provided they all have different address and that the pump 
connected to the PC has address 0. See manufacturer documentation for more info.

### Test connection
Now that you know the name of the serial port your pump is connected to you can instantiate a  


## Basic usage
lalla

## Advanced features
lalla

## MultiPump


## API docs
Autogenerate this