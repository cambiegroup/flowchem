# A Friendly Introduction

## Why use flowchem?

Flowchem was designed to assist in the development of automation in laboratories. Many electronic devices used in 
laboratories have different providers and different types of communication. To automate, for example, a set of devices 
to operate a process automatically, it is necessary:

* Define a programming coding language;

* Search with providers for ways to access the device using the chosen language;

* Develop the communication system using computer signal inputs like serial and Ethernet;

* Integrate all devices into a single system, where it is possible to start building protocols and instructions.

In addition to all the complexity involved in the steps presented, a factor that can be stressful is if there is a need 
to change a device during the construction or operation of the platform. This change will require rework to build the 
new device system, especially if it comes from a different supplier (with other communication, functions, and methods).

Flowchem connects with each device, ensuring easy access to all available commands through a web interface. This means 
that the user will not have to limit themselves to using a specific program language, as the connection to the devices 
can be easily accessed with a web data request package, which is present in most program languages (i.e., python, java, 
c++, HTML, and others).

Flowchem also has a high level of abstraction concerning devices. This abstraction occurs through the use of class, 
which represents components of a device, to build equipment. To explain better, look at the table below.

| Class of the system | Description        | Main function            | 
|---------------------|--------------------|--------------------------|
| Azura Compact Pump  | Device             | Communication Configure  |
| HPLC pump           | Component Specific | Specific access commands |
| Pump                | Component Base     | Base access commands     |
| Flowchem Component  | Class Base         | Base Constructor         |

When constructing a class to represent a device, as in our case, ***Azura Compact Pump*** inherits the attributes and 
methods of the class ***HPLC Pump***. This ***HPLC Pump*** class presents the specific standard commands for this pump 
category. In turn, this class inherits the attributes and methods of the class ***Pump***. This class has the most 
generic commands in all pumps (activate, infuse). This class still features the main class with attributes and methods 
present on all devices. This level of abstraction allows the user to switch from one device to another very quickly, 
as long as both devices have the same function (inherit the commands from ***HPLC Pump***, for example). It doesn't 
matter if they come from suppliers and have different communication protocols. This device exchange will occur without
changing anything in the already implemented code structure (a program related to the platform's automation). This 
change will only occur in the configuration file, which is easily editable.

## How easily editable is the configuration file?

Once installed, flowchem can be used. The first step to using the flowchem is to write the configuration file. This file
uses human-editable and friendly language. Each connected device must have a coding block, as shown below.

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
type = "ML600"             # Class name of the device
port = "COM5"              # Communication port
syringe_volume = "0.05 ml" # Additional configuration
```
Each block of code, separated by spacing, represents a device connected to the computer. The ***socl2***, ***hexyldecanoic***, 
***r4-heater***, ***flowir***, ***s-pump*** are the names of the devices. Its name is flexible enough to be editable by 
its users. The parameter type is the name of the implemented class that represents the device. See the devices available
and additional configurations in the [device configuration guides](../devices/supported_devices.md). This file needs to 
be saved with the extension ***.toml***. 

