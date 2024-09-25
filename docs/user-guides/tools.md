# Tools

There are additional tools in Flowchem to help users create the configuration file and utilize the API server.

## Autodiscover

Some devices implemented in Flowchem can be discovered using the autodiscover function present in Flowchem. To activate
this function, simply type the command in the command window.

```shell
flowchem-autodiscover
```

Autodiscover will examine the Ethernet input by sending and analyzing the data to identify the device connected to the
computer. The user can choose whether to also examine the serial channel.

```{warning}
The autodiscover include modules that involve communication over serial ports. These modules are *not* guaranteed to be
 safe. Unsupported devices could be placed in an unsafe state as result of the discovery process!
```

After the examination, a configuration file will be generated with the main characteristics of each identified device.
It's important to note that additional parameters may require adjustments. However, this feature saves time when 
creating the configuration file. The file named `flowchem_config.toml` created is placed in the flowchem package folder

## Accessing API

This function searches for flowchem devices on the network and returns a dictionary where the keys are device names
and values are API devices instances.

```python
from flowchem.client.client import get_all_flowchem_devices

devices = get_all_flowchem_devices()
```

This variable `devices` can be referred to as "client," as it is a client built on top of flowchem that utilizes its 
functionalities.

In a similar way that you can access the functionalities of the devices through the API, you can use the client devices.
For example, if you have an Elite11 pump, called *pumpG*, running on flowchem, you can send an infuse command to the 
pump 
with a volume 
of 10 ml and a flow rate of 1 ml/min through the API in the browser.

![](img.png)

With the client `devices`, this can be done in Python. Using the client `devices`, the construction of protocols directly 
in Python is facilitated.

```python
from flowchem.client.client import get_all_flowchem_devices

devices = get_all_flowchem_devices()

devices["PumpG"]["pump"].put("infuse", {"volume": "10 ml", "rate": "1 ml/min"})
```

The example shown in section [example](tutorials/examples/reaction_optimization.md) presents one way of how the 
protocols can be constructed.