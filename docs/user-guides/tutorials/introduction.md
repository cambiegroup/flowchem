# A Friendly Introduction

## Why use flowchem?

Flowchem was designed to assist in the development of automation in laboratories. Many electronic devices used in 
laboratories have different providers and different types of communication. To automate, for example, a set of devices 
to operate a process automatically, it is necessary:

* Define a programming coding language;

* Search with providers for ways to access the device using the chosen language;

* Develop the communication system using computer signal inputs like serial and Ethernet;

* Integrate all devices into a single system, where it is possible to start building protocols and instructions.

In addition to all the complexities involved in the steps presented, a factor that can be particularly stressful is the
need to change a device during the construction or operation of the platform. This change will require rework to build
the new system, especially if the new device is from a different vendor with different communications, functions, and
methods.

Flowchem connects with each device, allowing easy access to all commands through a web interface. Users are not 
restricted to a specific programming language, as they can access device connections using a web data request package 
available in most languages, including Python, Java, C++, and HTML.

Flowchem also has a high level of abstraction concerning devices. This abstraction occurs through the use of class, 
which represents components of a device, to build equipment. To explain better, look at the table below.

| Class of the system | Description        | Main function            | 
|---------------------|--------------------|--------------------------|
| Azura Compact Pump  | Device             | Communication Configure  |
| HPLC pump           | Component Specific | Specific access commands |
| Pump                | Component Base     | Base access commands     |
| Flowchem Component  | Class Base         | Base Constructor         |


When constructing a class to represent a device, such as the ***Azura Compact Pump***, it inherits the attributes and 
methods of the ***HPLC Pump*** class. This HPLC Pump class provides the standard commands specific to its pump 
category. In turn, the ***HPLC Pump*** class inherits the attributes and methods of the more generic ***Pump*** class, 
which includes basic commands common to all pumps (like activate and infuse). Furthermore, this ***Pump*** class 
inherits from a main class that contains attributes and methods applicable to all devices.

This level of abstraction allows users to switch between devices quickly, as long as the devices share the same 
function (i.e., inherit commands from the HPLC Pump class, for example). It doesn't matter if the devices come from 
different suppliers or have different communication protocols. This device exchange can be done without altering the 
existing code structure related to the platform's automation. The change is only needed in the configuration file, 
which is easily editable.

## Edit the configuration file

The configuration file is designed to be easily editable, allowing users to quickly make necessary changes without 
in-depth technical knowledge.

Flowchem uses a simple and human-readable format, TOML, which enables straightforward updates to device settings and 
parameters. This ensures that users can efficiently switch devices or modify configurations.

```toml
# Example of configuration flowchem file to access some devices
[device.socl2]
type = "Elite11"                 # Class name of the device
port = "COM4"                    # Communication access
syringe_diameter = "14.567 mm"   # Additional configuration
syringe_volume = "10 ml"         # Additional configuration
baudrate = 115200                # Additional configuration

[device.hexyldecanoic]
type = "AzuraCompact"          # Class name of the device
ip_address = "192.168.1.119"   # Communication access
max_pressure = "10 bar"        # Additional configuration

[device.r4-heater]
type = "R4Heater"              # Class name of the device
port = "COM1"                  # Communication access

[device.flowir]
type = "IcIR"                                     # Class name of the device
url = "opc.tcp://localhost:62552/iCOpcUaServer"   # Communication access
template = "30sec_2days.iCIRTemplate"             # Additional configuration

[device.s-pump]
type = "ML600"                # Class name of the device
port = "COM5"                 # Communication port
syringe_volume = "0.05 ml"    # Additional configuration
```

Each block of code, separated by key name, represents a device connected to the computer. The ***socl2***, 
***hexyldecanoic***, ***r4-heater***, ***flowir***, ***s-pump*** are the key names of the devices. Its name is flexible 
enough to be editable by its users. In other words, The user can choose to name the devices according to their 
preference. 

The parameter type is the name of the implemented class that represents the device. See the devices available
and additional configurations in the [device configuration guides](../reference/devices/supported_devices.md). This file needs to be saved with the 
extension ***.toml***. 

