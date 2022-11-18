# Software architecture

## Repository structure
The repository is structured as follows:
* `docs` - documentation
* `examples` - example of use
* `src` - source code
* `tests` - test files (pytest)
We follow the "src-layout", read [this article](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#src-layout) for more details.

Moreover, the source code in the `flowchem` packages is organized in:
* `components` - the abstract components representing specific device capabilities (e.g. pumping).
* `devices` - containing the code to control the different devices, sorted by manufacturer
* `server` - the modules related to configuration parsing and API server initializaiton.
* `utils` - various helper functions

## flowchem command
At its core, flowchem is a command line application that:
1. parse a configuration file
2. connects to the lab devices described and
3. offer access to them via a RESTful API.

All of this can be achieved without installing anything via pipx run, e.g.
```shell
pipx run flowchem my_device_config.toml
```

## Flowchem server startup
When the CLI command `flochem` is called, the following happens:
1. The configuration file provided as argument is parsed, and the device objects are created in the order they appear in the file.
2. Communication is established concurrently for all the devices via calls to each object's `initialize()` method.
3. The components of each hardware object are collected, their routes added to the API server and advertised via mDNS.
4. Flowchem is ready to be used.

It follows that:
* All the code in components (step 3) can assume that a valid connection to the hw device is already in place (step 2).
* Components can use introspection on the relevant hardware device object, e.g. to determine if a pump has withdrawing
  capabilities or not.
* The devices are validated during the initialization and are expected to raise exceptions only during the server startup.
* For safety reasons, all exceptions thrown after the server startup, i.e. during the server lifetime, are caught.
  This ensures that potential errors on one device do not affect the operation of the other devices on the same server.

## FAQ

%### Why no device orchestration functionalities are included?
%Lab automation holds great potential, yet research lab rarely reuse existing code.
%One reason for this is the lack of modularity in the existing lab-automation solutions. While a monolithic approach is faster to implement, it lacks flexibility.
%We designed flowchem to be a solid foundation for other modules to be based on.
%We try to follow the unix philosophy: do one thing, and do it well. Flowchem provides uniform API endpoints for the heterogeneous environment of lab devices.

%### Why Python 3.10?
%The recommended use of flowchem is to run it as standalone app to provide homogeneous REST API access to the variegated landscape of lab devices. The direct import of device objects is highly discouraged.
%This allows us to use a recent version of Python and to exploit all the newly introduced features.
%For example, in the codebase are used the walrus operator (`:=`) and `importlib.metadata` introduced in 3.8, the dict merge with OR operator introduced in 3.9 and the type hints unions with the OR operator introduced in 3.10. We are looking forward to the inclusion of `tomllib` in the stdlib for 3.11 to drop the external dependency on `tomli`.

%### Why FastAPI?
%To create the API endpoints we use fastAPI mainly for its simplicity and for the ability to automatically generate openAPI specs from the type hints.
%The async aspects were particularly appealing since the communication with lab devices can take relatively long time (especially on slow protocols such as serial communication at 9600 baud) thus impacting the responsiveness of the API even at low requests/second.

%### Why Pint?
%Different devices use different units for the same quantities. For example, among pumps, Knauer HPLC pumps use ul/min as base unit, Harvard Apparatus syringe pumps can be set with different units from the nl/h to the ml/s while the Hamilton ML600 pumps have a custom steps-per-stroke parameter that controls the flow rate.
%Moreover, to offer a uniform experience and prevent errors, the same units should be used by the public API across different devices, yet the order of magnitudes involved are often experiment-specific.

%To solve all of these problems we decided to adopt [pint](https://pint.readthedocs.io/en/stable/) to represent any physical quantity. Particularly attractive was the possibility of serialize and de-serialize the quantities to strings with minor losses in precision. This matched our aim of enabling full configurability of device settings via a simple, text-based configuration file. For example, a syringe diameter can be intuitively specified as either "18.2 mm" or "1.82 cm".

Principles:
- No-code shim: device settings via YAML file creates OpenAPI endpoints with predictable names based on serial numbers.
- Implements existing interoperable standard for lab IoT to avoid standard proliferation.

Implementation design:
  - ideally all permanent device specific parameters (not changing during normal use) are received/set in a uniform way and advertised as such (to enabling dynamic graphs config via web interface, somehow similar to Magritek protocol options).
- Don't force code-reuse, but allow for easy extension and leave device modules as independent as possible.
- Each device has a name, unique per server, tha will be the endpoint path.

To provide the best possible experience for users, flowchem took inspiration from different aspects of packages with
similar aims, including (in alphabetical order):
- [Chemios](https://github.com/Chemios/chemios)
- [ChemOS](https://github.com/aspuru-guzik-group/ChemOS)
- [MechWolf](https://github.com/MechWolf/MechWolf)
- [Octopus](https://github.com/richardingham/octopus)
