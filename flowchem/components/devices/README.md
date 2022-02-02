# flowchem/components

This folder contains all the components that appear in a device graph.

Those include the following:
* Abstract base classes defining the properties that actual device component can implement in [properties](properties/README.md)
* Simple modular components such as mixers and tubing in [stdlib](stdlib/README.md) 
* actual hardware devices in [devices](devices/README.md)
* dummy object for testing purposes in [dummy](dummy/README.md)
* pre-defined reactor assembly, i.e. sub-graphs representing hardware that is logically composed by several non-separable components e.g. in a chip reactor in [reactors](reactors/README.md)