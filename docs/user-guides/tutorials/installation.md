# Install flowchem
Flowchem requires a Python version of 3.10 or later.
You can get the latest version of Python from [python.org](https://www.python.org/downloads/).

To get started with flowchem run (preferably in a dedicated [virtual environment](https://peps.python.org/pep-0405/)):
```shell
pip install flowchem
```
or install it with [pipx](https://pypa.github.io/pipx/), a tool to install and run python applications in isolated
environments:
```shell
pip install pipx
pipx ensurepath
pipx install flowchem
```
Another way to install the package can be done through the Anaconda prompt:
```shell
conda install flowchem
```

<!--
The use of `pipx` is recommended because it:
* installs flowchem in a virtualenv, without interfering with other packages installed globally;
* ensure that the `flowchem` and `flowchem-autodiscover` commands are available system-wide, by adding the pipx binary
  folder to the system PATH (the `pipx ensurepath` step).-->

To verify the installation has been completed successfully you can run `flowchem --version`.
