# flowchem/components/devices

This folder contains all the components that appear in a device graph.

For real device graph, only components from **stdlib**, **devices** and **assemblies** should be used.

This folder includes:
* Simple modular components such as mixers and tubing in [stdlib](stdlib/README.md)

* actual hardware devices in [devices](devices/README.md)

* pre-defined reactor assembly, i.e. sub-graphs representing hardware that is logically composed by several non-separable components e.g. in a chip reactor in [assemblies](./assemblies/README.md)

* Abstract base classes defining the properties that actual device component can implement in [properties](properties/README.md)

* dummy object for testing purposes in [dummy](dummy/README.md)
(assemblies/README.md)
