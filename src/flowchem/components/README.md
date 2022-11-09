# flowchem/components

This folder contains the models (i.e. abstract base classes) that define the public API of the components exposed by
flowchem devices.

Ideally, for components of the same type (e.g. SyringePumps) it should be possible to change from one manufacturer to
another one by simply updating the configuration file, while the public API remains unchanged.

It is, however, still possible for individual devices to support additional commands, beyond the minimum set defined by
this specs.
Even if available, the use of such commands is discouraged as it limits the applicability of any derived code.

For a list of all the different component types consult the documentation.
