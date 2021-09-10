# flowchem
Flowchem is a {BRIEF DESCRIPTION}

Test it now with pipex!

Principles:
- No-code platform: device settings via YAML file and method calls via OpenAPI (directly usable in the browser).
- only specify settings in a config file, `pipex` the module and use the OpenAPI (e.g. testing via web-broswer).
- cross-platform HTTP-based API interface for interoperability. (This circumvents the issues with python dependencies and versioning conflicts and allows us to use modern python.
- it should still be possible to interact with the device object directly, i.e. without the HTTP interface, for power-users.

Implementation design:
- The end user should not need any knowledge of any implementation detail. Underlying complexity has to be handled internally and hidden to the user. 
- Device objects should only raise Exceptions upon instantiation.
  - the connection to the device is implicit in the object instantiation
  - raising warning is the preferred way to signal errors during execution as it allows the control code to continue w.g. with cleanup
  - communication streams are passed to the device constructors (i.e. dependency injection). This simplifies testing.
- Each device module should be independent. Code sharing is possible via flowchem.analysis (or flowchem.utils et simil.) 
- Each device module should be accompanied by tests and documentation (at least in form of examples).
- Device objects should use generic flowchem.exceptions or sublcasses thereof.