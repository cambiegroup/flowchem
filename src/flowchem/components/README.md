# flowchem/components

This folder contains the model components defining the public API of flowchem devices.

Ideally, for components of the same type (e.g. SyringePumps) it should be possible to change from one manufacturer to
another one by simply updating the configuration file, while the public API remains unchanged.

It is, however, still possible for individual devices to support additional commands, beyond the minimum set defined by
this specs.  The use of such commands is discouraged as it limits the portability of any derived code.

For a list of all components consult the documentation.
