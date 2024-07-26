# Getting started
Flowchem is a Python package designed to enable users to establish an API for accessing laboratory devices through a web interface. It provides tools to help users automate processes across a range of devices from different manufacturers, allowing them to work together seamlessly to carry out experimental processes automatically.
	
Flowchem was developed by chemists to apply in the platform construction of chemical synthesis. Its main features:
	
1. Has a friendly notation in which devices accessed are built by a configuration file. This file is easily understandable and editable.
2. creates connections with each device and ensures a reproducible state at start-up;
3. provides access to the capabilities of each device (such as pumping, heating etc...) via a web interface.

:::{figure-md} flowchem-architecture
<img src="architecture_v1.svg" alt="Flowchem software architecture (devices/config/server)" class="bg-primary mb-1" width="100%">

**Figure 1** Schematic representation of flowchem software architecture.
A heterogeneous collection of devices is physically connected to a control PC.
The configuration file in TOML format specifies the connection parameters for each device.
After running flowchem with that configuration, a web server is started to control each device via a single API.
:::

### Interoperability
Since flowchem leverages web technologies, flowchem devices can be controlled directly with a web browser or by clients
written in different languages and from almost any operative system, including Android and iOS.
A set of python clients interfacing with the flowchem API are also provided and used in examples.

To the reader who wants to go directly to the matter, follow the instructions in the [tldr](tldr.md).

We recommend the user have an excellent immersion and introduction to the package to follow the following readings.

1. How to [install](user-guides/tutorials/installation.md) the Flowchem;
2. Read a [introduction](user-guides/tutorials/introduction.md) to learn why, when, and where to use the package. 
3. How do you [run](./configuration_file) the package using an example file configuration? 
4. Start to learn how the user can access the [API](user-guides/how-to-guides/using_api.md).
5. Read an [exemple](user-guides/explanation/examples/index.md) case in which the package was applied.