Harvard Apparatus Elite 11
==========================

Flowchem implements the Protocol11 syntax to communicate with Elite11 pumps.

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

### Model type
Note that there are two models of Elite11, an "infuse only" and an "infuse and withdraw" pump.
If you only need infuse capabilities just use:
```python
from flowchem import Elite11InfuseOnly
```
this will work with both pump models.
On the other hand, if you need withdraw commands you need:
```python
from flowchem import Elite11InfuseWithdraw
```
whose `initialize()` method will take care of ensuring that the pump supports withdrawing.

The constructor and all the methods are the same for both `Elite11` pumps, with the exception of the withdrawing commands being
only available in `Elite11InfuseWithdraw`.


## Test Connection
Now that you know the serial port your pump is connected to, and the model of your pump, you can instantiate it and test the connection.
```python
from flowchem import HarvardApparatusPumpIO, Elite11InfuseWithdraw
pumpio = HarvardApparatusPumpIO(port='COM4')
pump1 = Elite11InfuseWithdraw(pump_io=pumpio, diameter=10.2, syringe_volume=10, address=0)
pump2 = Elite11InfuseWithdraw(pump_io=pumpio, diameter=10.2, syringe_volume=10, address=1)

```
Alternatively, the `from_config()` classmethod can be used to instantiate the pump without the need of creating an
HarvardApparatusPumpIO object (will be done automatically and shared across pumps on the same serial port).
```python
from flowchem import Elite11InfuseWithdraw
pump = Elite11InfuseWithdraw.from_config(port="COM4", address=0, diameter="14.5 mm", syringe_volume="10 ml", name="acetone")
# Note that the constructor above is equivalent to the following
pump_config = {
    'port': 'COM4',
    'address': 0,
    'name': "acetone",
    'diameter': "14.6 mm",
    'syringe_volume': "10 ml"
}
pump = Elite11InfuseWithdraw.from_config(**pump_config)
# ... which is what is actually used when a device configuration is provided in yaml format e.g. via graph file.
```

## Initialization
The first step after the creation of the pump object is the initialization, via the `initialize()` method, e.g.:
```python
await pump.initialize()
```
Note that the `initialize()` method returns a coroutine, so it must be called with `await` in order to wait for the pump to be ready.
If you are not familiar with asynchronous syntax in python you can just call it with `asyncio.run()`.
```python
import asyncio
asyncio.run(pump.initialize())
```
The initialization is needed to find the pump address if non was provided (the autodetection only works if a single pump is
present on the serial port provided), to set the syringe volume and diameter and to ensure that the pump supports
withdrawing moves if it has been initialized as `Elite11InfuseWithdraw`.

## Usage
Once you've initialized the pump, you can use all the methods it exposes. See FIXME:add sphinx autodoc link for the API reference.

## API docs
Autogenerate this
