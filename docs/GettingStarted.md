# flowchem: the basics for new users

Welcome to the new users guide to flowchem!
If you have comments or suggestions, please don’t hesitate to [reach out](./Community.md)!

## Welcome to flowchem!

Flowchem is a python library to control a variety of instruments commonly found in chemistry labs.

## Installing flowchem
While the RESTful API created by flowchem can be consumed from different programs and programming languages, flowchem
itself is written in the popular open-source language Python.

If you already have Python version 3.10 or above, you can install flowchem with:
```shell
pip install flowchem
```

If you don’t have Python yet, you can download it from [python.org](https://www.python.org/downloads/).

## How to use flowchem
Flowchem simply needs a device configuration file that specify the connection settings for the different devices
that you want to control.

Let's start by creating a simple configuration file defining the connection to a test device: a fake HPLC pump.
You can save this file as `my-devices.toml`.
```toml
simulation = true

[device.test-device]
type = "FakePump"
port = "COM11"
max_pressure = "10 bar"
```

```{note} my-devices.toml
Technically, this file is in [TOML format](https://en.wikipedia.org/wiki/TOML). The syntax of TOML has been designed to be as intuitive and human-editable as possible, so if you follow this guide you will intuitively understand all
that you need without the need to read the language specification.
```
