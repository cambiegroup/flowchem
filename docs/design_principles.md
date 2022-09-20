# Software architecture

## General
### Why no device orchestration functionalities are included?
Lab automation holds great potential, yet research lab rarely reuse existing code.
One reason for this is the lack of modularity in the existing lab-automation solutions. While a monolithic approach is faster to implement, it lacks flexibility.

We designed flowchem to be a solid foundation for other modules to be based on.

We try to follow the unix philosophy: do one thing, and do it well. Flowchem provides uniform API endpoints for the heterogeneous environment of lab devices.

### Why Python 3.10?
The recommended use of flowchem is to run it as standalone app to provide homogeneous REST API access to the variegated landscape of lab devices. The direct import of device objects is highly discouraged.
This allows us to use a recent version of Python and to exploit all the newly introduced features.
For example, in the codebase are used the walrus operator (`:=`) and `importlib.metadata` introduced in 3.8, the dict merge with OR operator introduced in 3.9 and the type hints unions with the OR operator introduced in 3.10. We are looking forward to the inclusion of `tomllib` in the stdlib for 3.11 to drop the external dependency on `tomli`.

### Why FastAPI?
To create the API endpoints we use fastAPI mainly for its simplicity and for the ability to automatically generate openAPI specs from the type hints.
The async aspects were particularly appealing since the communication with lab devices can take relatively long time (especially on slow protocols such as serial communication at 9600 baud) thus impacting the responsiveness of the API even at low requests/second.

### Why Pint?
Different devices use different units for the same quantities. For example, among pumps, Knauer HPLC pumps use ul/min as base unit, Harvard Apparatus syringe pumps can be set with different units from the nl/h to the ml/s while the Hamilton ML600 pumps have a custom steps-per-stroke parameter that controls the flow rate.
Moreover, to offer a uniform experience and prevent errors, the same units should be used by the public API across different devices, yet the order of magnitudes involved are often experiment-specific.

To solve all of these problems we decided to widely adopt [pint](https://pint.readthedocs.io/en/stable/) to represent any physical quantity. Particularly attractive was the possibility of serialize and de-serialize the quantities to strings with minor losses in precision. This matched our aim of enabling full configurability of device settings via a simple, text-based configuration file. For example, a syringe diameter can be intuitively specified as either "18.2 mm" or "1.82 cm".

### Repository structure
We follow the so-called "src-layout" i.e. with the source code in a `src` sub-folder. This increasingly popular trend among the Python ecosystem is to ensure that tox (among others) is using the built version of flowchem and not the local folder shadowing the same namespace. Read [this article](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#src-layout) for more details.

### CLI application
At its core, flowchem is a command line application that:
1. parse a configuration file
2. connects to the lab devices described and
3. offer access to them via a RESTful API.

All of this could in theory be achieved without installing anything via pipx run, e.g.
```shell
pipx run flowchem my_device_config.toml
```

Principles:
- No-code shim: device settings via YAML file creates OpenAPI endpoints with predictable names based on serial numbers.
- Implements existing interoperable standard for lab IoT to avoid standard proliferation.

Implementation design:
- intended use via CLI endpoint, installed via `pipex`.
- Ideally, failure in one device should not affect the others. (Catch-all error via starlette middleware SO 61596911)
- to ease debug, add support for auto-reload if settings file is changed. (easy, need to trigger reload on changes, via watchfiles)
- only connection specific settings are needed. Device-specific are optional on instantiation even if needed for use.
  - This e.g. a syringe pump might need syringe diameter and volume before use, but those are device specific parameters and not connection specific, so they are not required in flowchem config.
  - ideally all permanent device specific parameters (not changing during normal use) are received/set in a uniform way and advertised as such (to enabling dynamic graphs config via web interface, somehow similar to Magritek protocol options).
- Don't force code-reuse, but allow for easy extension and leave device modules as independent as possible.
- Each device module should be accompanied by tests and documentation/examples.
- Following abstract device ontologies ease abstraction in higher level code.
- Each device MUST have a name, unique per server, tha will be the endpoint path.  If Non will be generated.
  - If a unique name can be programmatically used after init (e.g. based on SERIAL_NUMBER), than that will be also advertised in autodiscover name.
  - This allows dependent libraries to use static names even though they are not yet known at flowchem init.

Inspired by many packages with similar aims, including (in alphabetical order):
- [Chemios](https://github.com/Chemios/chemios)
- [ChemOS](https://github.com/aspuru-guzik-group/ChemOS)
- [MechWolf](https://github.com/MechWolf/MechWolf)
- [Octopus](https://github.com/richardingham/octopus)
