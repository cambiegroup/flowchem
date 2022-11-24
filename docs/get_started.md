# Get started guide

This guide will guide you through the installation and setup of a flowchem server.


## Install flowchem
Flowchem is a command-line tool that generates an API to control a variety of instruments commonly found in chemistry
labs. To use it, you need to have Python installed. Flowchem requires a Python version of 3.10 or later.

To get started with flowchem run:
```shell
pip install flowchem
```
or install it with `pipx`:
```shell
pip install pipx
pipx ensurepath
pipx install flowchem
```

The use of `pipx` is the recommended way because it will:
* install flowchem in a virtualenv, without interfering with other packages installed globally
* ensure that the `flowchem` and `flowchem-autodiscover` commands are available system-wide, by adding the pipx binary
  folder to the system PATH.

If you don’t have Python yet, you can download it from [python.org](https://www.python.org/downloads/).

To verify the installation has been completed successfully you can run `flowchem --version`.

## Generate configuration file
To autogenerate a flowchem configuration file, run the autodiscover tool:
```shell
flowchem-autodiscover
```
This will auto-detect a variety of devices connected to your computer and generate a `flowchem_config.toml` file with a
configuration stub for all the devices detected.
Complete the missing information (if any) in this file, and then you will be ready to use flowchem!

```{note}
`flowchem_config.toml` is written in [TOML format](https://en.wikipedia.org/wiki/TOML),
the syntax of this language is intuitive and designed to be human-editable.
If you follow this guide you will not need to learn anything about the TOML syntax, but you can just copy and modify the
examples provided.
```

:::{note}
Not all the devices supported by flowchem can be auto discovered, so you might need to edit the configuration
file manually for some device types.
:::

## Run flowchem
With flowchem installed and a configuration file created, you are ready to start your flowchem server.

Run `flowchem` followed by the location of the configuration file:
```shell
flowchem flowchem_config.toml
```

In your terminal, you will see some debug information, ending with a line like this one:
```shell
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

This means that the flowchem server has been started correctly.
You can visit [http://127.0.0.1:8000](http://127.0.0.1:8000) to see a list of commands available for the device you
configured.

For every request sent to the flowchem server, you will see some diagnostic output in the terminal.
While you can normally ignore this output, it can provide useful information in case of errors.
