# Phidgets
```{admonition} Additional software needed!
:class: attention

To control the Phidget devices you need to install their software first.
Visit the [phidget website](https://www.phidgets.com/docs/Main_Page) for more details.
```

# Phidgets Bubble Sensor
```{admonition} Additional software needed!
:class: attention

To control the Phidget devices you need to install their software first.
Visit the [phidget website](https://www.phidgets.com/docs/Main_Page) for more details.
```
## Bubble Sensor
Following the same philosophy as the [pressure sensor](phidget_pressure_sensor.md), the bubble sensor was built 
using light sensors connected to the 
[Versatile Input Phidget](https://www.phidgets.com/?tier=3&catid=49&pcid=42&prodid=961).

The configuration file for accessing such devices is described below:

```toml
[device.virtual-phidgets-pressure]
type = "VirtualPhidgetBubbleSensor"
vint_serial_number = -1          # (Optional)
vint_hub_port = -1               # (Optional)
vint_channel = -1                # (Optional)
phidget_is_remote = False        # (Optional)
data_interval = 250  # ms        # (Optional)
```

For more details, see the communication library available on the official Phidget website.

