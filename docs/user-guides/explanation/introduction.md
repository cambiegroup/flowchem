# Overview

Flowchem was designed to assist in the development of laboratory automation. Many electronic devices used in 
laboratories have different suppliers and different types of communication. Flowchem enables the automation of a 
set of devices to operate a process automatically. This overview aims to help the reader better understand the two 
main features and concepts addressed by the package.

## flowchem Configuration File: Simple, Flexible, and User-Friendly

FlowChem uses a TOML (Tom's Obvious, Minimal Language) configuration file to manage device settings. This format was 
chosen for its simplicity and readability, making it easy for users to edit without requiring extensive technical 
knowledge.

### Key Features of the Configuration File

1. **Human-Readable Format**: TOML is designed to be easy to read and write, using simple key-value pairs and sections.

2. **Flexible Device Naming**: Users can name devices according to their preference, enhancing clarity and organization.

3. **Easy Updates**: Changing device settings or switching devices can be done quickly by editing the relevant sections.

4. **Clear Structure**: Each device is represented by its own block, making the file easy to navigate and understand.

### Understanding the File Structure

```toml
[device.user_chosen_name]
type = "DeviceClass"
communication_parameter = "value"
additional_parameter1 = "value1"
additional_parameter2 = "value2"
```

- **Device Block**: Starts with `[device.user_chosen_name]`. The name (e.g., socl2, hexyldecanoic) can be freely chosen by the user.
- **Type**: Specifies the device class (e.g., "Elite11", "AzuraCompact").
- **Communication Parameter**: How to connect to the device (e.g., port, IP address, URL).
- **Additional Parameters**: Any extra settings specific to the device type.

### Example Breakdown

Let's look at one device from the example:

```toml
[device.socl2]
type = "Elite11"                 # Class name of the device
port = "COM4"                    # Communication access
syringe_diameter = "14.567 mm"   # Additional configuration
syringe_volume = "10 ml"         # Additional configuration
baudrate = 115200                # Additional configuration
```

- The device is named "socl2" (user's choice).
- It's an "Elite11" type device.
- It's connected via COM4 port.
- It has specific syringe and communication settings.

### Editing the File

1. **Changing Device Names**: Simply edit the `[device.name]` line.
2. **Updating Settings**: Modify the values after the `=` sign.
3. **Adding/Removing Devices**: Add or delete entire `[device.name]` blocks as needed.

```{warning}
When editing, ensure that:
- The `type` parameter matches an implemented device class in FlowChem.
- The communication parameter (port, IP, URL) is correct for your setup.
- Any additional parameters are appropriate for the device type.
```

### File Usage

1. Make your changes in the TOML file.
2. Save the file with a `.toml` extension.
3. FlowChem will use this configuration to connect to and manage the devices.

For detailed information on supported devices and their specific configuration options, refer to the 
[device configuration guides](../reference/devices/supported_devices.md).

This user-friendly approach allows for quick adjustments to your FlowChem setup, enabling efficient management of 
various devices without the need for complex programming or system changes.

## Abstraction

FlowChem employs a high level of abstraction for devices through the use of 
[class and inheritance](https://pythonbasics.org/inheritance/). This approach allows the system to represent device 
components and build equipment efficiently. To illustrate, consider the table and figure below:

| Class of the System   | Description        | Main Function            |
|-----------------------|--------------------|--------------------------|
| Azura Compact Pump    | Specific Device    | Implement & run Commands |
| HPLC Pump             | Specific Component | Define Specific Commands |
| Pump                  | Base Component     | Define Base Commands     |
| FlowChem Component    | Base Class         | Base Constructor         |

### How Inheritance Works in FlowChem

When creating a class to represent a device, such as the ***Azura Compact Pump***, it inherits attributes and methods 
from the ***HPLC Pump*** class. The ***HPLC Pump*** class provides standard commands specific to its category of pumps.
This class, in turn, inherits from a more generic ***Pump*** class, which includes basic commands common to all pumps,
such as `activate` and `infuse`. Furthermore, the ***Pump*** class inherits from a base class that contains attributes
and methods applicable to all devices.

### Benefits of This Abstraction

1. **Ease of Device Switching**: Users can quickly switch between devices that share the same functions (i.e., inherit 
commands from the same parent class). This is possible even if the devices come from different suppliers or use different communication protocols.
2. **Minimal Code Changes**: Switching devices requires no changes to the existing code structure related to the 
platform's automation. The only change needed is in the configuration file, which is easily editable.
3. **Code Reusability**: By using inheritance, FlowChem avoids code duplication. Methods and attributes defined in a 
parent class are automatically available in all child classes, promoting the principle of "Don't Repeat Yourself" (DRY).

### Example

Consider the following hierarchy:

![](inherit.JPG) 

1. **FlowChem Component**: The base class for all devices.
2. **Pump**: Inherits from FlowChem Component, includes basic pump commands.
3. **HPLC Pump**: Inherits from Pump, includes specific commands for HPLC pumps.
4. **Azura Compact Pump**: Inherits from HPLC Pump, includes configuration for a specific device model.

This structure allows the ***Azura Compact Pump*** to utilize all the commands and attributes defined in its 
parent classes, ensuring consistent behavior and easy integration.

### Practical Impact

This level of abstraction ensures that users can manage and configure devices with minimal effort, focusing on 
high-level functionality rather than low-level implementation details. The configuration file, written in a simple 
and human-readable TOML format, allows users to make necessary changes quickly and efficiently.

Citations:
[1] https://pythonbasics.org/inheritance/
