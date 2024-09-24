# Configuring and running a real device

Before proceeding with the instructions on how to set up and operate a real device, it's important to have a good
understanding of the configuration file and how to interact with the API server. While the 
"[How to create a configuration file](configuration.md)" and 
"[How to work with API](using_api.md)" 
sections illustrate these concepts using fake devices, the underlying principles remain the same when working with a 
real device.

For this tutorial, we have selected the Knauer Valve. The settings, as documented in the 
[reference material](../reference/devices/valves/knauer_valve.md), are outlined in the following configuration file, 
named config.toml. 

```toml
[device.my-knauer-valve]  # This is the valve identifier
type = "KnauerValve"  # The actual valve type will be detected automatically
ip_address = "169.254.31.44"  # Onyl one of either ip_address or mac_address need to be provided
mac_address = "00:80:A3:B4:CE:77"  #  Onyl one of either ip_address or mac_address need to be provided
```



