Welcome to flowchem
===================


![github-actions](https://github.com/cambiegroup/flowchem/actions/workflows/python-app.yml/badge.svg)
[![PyPI version fury.io](https://badge.fury.io/py/flowchem.svg)](https://pypi.org/project/flowchem/)
[![Documentation Status](https://readthedocs.org/projects/flowchem/badge/?version=latest)](https://flowchem.readthedocs.io/en/latest/?badge=latest)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![DOI](https://zenodo.org/badge/300656785.svg)](https://zenodo.org/badge/latestdoi/300656785)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_of_CONDUCT.md)

Flowchem is a python library to control a variety of instruments commonly found in chemistry labs.

### Overview
Using flowchem is simple. You only need to
1. **Create a configuration file** with the connection parameters for the devices you want to control (see the
[User Guide](https://flowchem.readthedocs.io/en/latest/user_guide.html) for details).
2. **Run `flowchem my_device_config_file.toml`** with the name of your configuration file
3. **Done**!
A web server will be created serving a RESTful API endpoint for each device, directly
usable in browser or programmatically.

### Supported devices
Currently, the following instruments are supported, but we are open to contributions and the list keeps expanding!
 - Pumps (Knauer P2.1, Harvard Apparatus Elite 11, Hamilton ML600)
 - Valves (ViciValco and Knauer)
 - Thermostat (Huber)
 - Analytical instruments (Magritek Spinsolve benchtop NMR and Mattler Toledo FlowIR)
 - General purpose sensors-actuators from Phidgets (e.g. 4...20 mA sensor to interface with Swagelok pressure sensors)
 - ... [add support for a new device](https://flowchem.readthedocs.io/en/latest/add_new_device_type.html)!

## Installation
To install flowchem, Python >= 3.10 is needed.
If you plan to use flowchem as a used, without modifing its source code, we suggest to install it with pipx.
You can install pipx and flowchem as follows:
```shell
pip install pipx
pipx ensurepath
pipx install flowchem
```
This will make the `flowchem` and `flowchem-autodiscover` commands available system-wide.

## Documentation
You can find the documentation online on [flowchem.readthedocs.io](https://flowchem.readthedocs.io/en/latest/).

## License
This project is released under the terms of the MIT License.

## Questions
For questions about this project, fell free to open a GitHub issue, or reach out
[by email](mailto:2422614+dcambie@users.noreply.github.com).
