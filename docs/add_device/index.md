# Add support for new devices

If you want to add support for a new device-type this is tha page for you!
Let's assume you got a new lab device, an _✨Extendable Ear✨_ manufactured by _Weasley & Weasley_.
And of course you want to control it via flowchem. Solid idea!👏

You have two possibilities:
* add support directly into flowchem (fork the repo, add device-specific code and
create a pull request)
* add support via a plugin (e.g. a `flowchem-extendable-ear` package)

In general, devices whose support needs the addition of new dependencies to flowchem are better packaged as plugins,
while generally useful modules are ideally embedded with flowchem.
This is to limit the amount dependencies in `flowchem` while enabling support to devices with more complex needs.

For example, a device only needing serial communication such as a syringe pump is ideal for native support, while the
interface to Spinsolve NMR, that needs an external library form XML parsing, is provided as a plugin.

```{toctree}
:maxdepth: 2
:caption: Add device to flowchem

add_to_flowchem
add_as_plugin

```
