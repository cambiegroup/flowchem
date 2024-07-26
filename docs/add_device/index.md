# Add support for new devices

If you want to add support for a new device-type this is the page for you!
Let's assume you got a new lab device, an _👂Extendable Ear👂_ manufactured by _Weasley & Weasley_.
But how to control it via flowchem?

You have two possibilities:
* [add support directly into flowchem](./add_to_flowchem.md)
* [add support via a plugin](./add_as_plugin.md)

In general, devices that need the addition of several new dependencies to flowchem are better packaged as
plugins, while generally useful modules are ideally embedded with flowchem.
This is to limit the amount dependencies in `flowchem` while enabling support to devices with more complex needs.

Currently, the only plugin to `flowchem` is [flowchem-test](https://pypi.org/project/flowchem-test/) which adds a
barebone device type called FakeDevice for use in tests.

```{toctree}
:maxdepth: 2
:hidden:

add_to_flowchem
add_as_plugin
```
