# Getting started

Flowchem's package assists the user in building the automation of your platform. Here, the 
platform is understandable as a conjunct of devices, generally of different suppliers, that must work synchronized to 
accomplish a task. In other words, to perform an experimental process automatically. 

If you're already familiar with the package or want to get straight to the point, just follow the instructions in this 
[ltdr](tldr.md).

:::{figure-md} flowchem-architecture
<img src="architecture_v1.svg" alt="Flowchem software architecture (devices/config/server)" class="bg-primary mb-1" width="100%">

**Figure 1** Schematic representation of flowchem software architecture.
A heterogeneous collection of devices is physically connected to a control PC.
The configuration file in TOML format specifies the connection parameters for each device.
After running flowchem with that configuration, a web server is started to control each device via a single API.
:::

## Key features of the flowchem

1. **Easy configuration**

Flowchem was designed to use a simple, editable configuration file. This file contains the names of the devices 
connected to the computer and key details about each one, such as their connection addresses.

2. **Abstraction**

Flowchem was built using a class hierarchy for each component. Each device inherits common methods and attributes 
shared among similar devices. If needed, some devices can be easily replaced with an equivalent one without losing 
functionality. These equivalent devices can come from different suppliers but perform the same function, like two 
different pumps.

3. **Reproducible**

Flowchem creates connections with each device and ensures a reproducible state at start-up;

4. **Multithreading**

Flowchem provides access to the capabilities of each device (such as pumping, heating etc...) via a web interface.
Flowchem was developed to work with multithreading using the 
[Asynchronous package](https://docs.python.org/3/library/asyncio.html). This means commands can be sent 
asynchronously, and each device will run in its own thread. This setup helps prevent the entire system from crashing 
if an error occurs with one device.

5. **Interoperability**:

Since flowchem leverages web technologies, flowchem devices can be controlled directly with a web browser or by clients
written in different languages and from almost any operative system, including Android and iOS.
A set of python clients interfacing with the flowchem API are also provided and used in examples.

We recommend the user have an straightforward immersion to the package to follow the following readings.

1. Follow the instruction to [install](user-guides/tutorials/installation.md) the package;
2. Read the instructions to create the [configuration file](user-guides/tutorials/configuration.md);
3. Read how using the [API](user-guides/tutorials/using_api.md) built;
4. Read an [exemple](user-guides/explanation/examples/index.md) case in which the package was applied. 

The main concepts of the package and a detailed explanation of its key features are covered in the 
[explanations](user-guides/explanation/index.md).
