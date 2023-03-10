# Flowchem

Flowchem is an application to simplify the control of instruments and devices commonly found in chemistry labs.
Flowchem acts as unifying layer exposing devices using different command syntax and protocols under a single API.

<!--
See https://sphinx-design.readthedocs.io/en/latest/grids.html and https://getbootstrap.com/docs/5.0/layout/grid/
-->
::::{grid} 1 2 3 4

:::{grid-item}
:columns: auto

```{button-ref} getting_started
:color: primary
:tooltip: Getting started guide
```
:::
:::{grid-item}
:columns: auto

```{button-ref} learning/tutorial
:color: secondary
:tooltip: Introductory tutorial - learning-oriented practical steps
```
:::
:::{grid-item}
:columns: auto

```{button-ref} examples/index
:color: secondary
:tooltip: Introductory tutorial - task-oriented practical steps
```
:::
:::{grid-item}
:columns: auto

```{button-ref} api/index
:color: secondary
:tooltip: API reference - information-oriented theoretical knowledge
```
:::
::::

## Supported devices
The list of all supported devices [is available here](devices/supported_devices)!

## Install flowchem
To install flowchem, ensure you have Python installed, then run:
```shell
pip install flowchem
```
More information on [installing flowchem](./getting_started.md).

## Tutorial
Follow the [Introduction tutorial](./learning/tutorial.md) for a hands-on introduction to flowchem:

<!--
## Examples
See some example of the use of flowchem in automated reaction control systems!

```{button-ref} Example 1
:color: primary
```
```{button-ref} Example 2
:color: primary
```
-->

<!--
TODO: add ref to paper once out.
## Citation
If you use flowchem for your paper, please remember to cite it!
-->

## Contents
```{toctree}
:maxdepth: 2
:caption: User Guide

getting_started

learning/tutorial

devices/supported_devices

examples/index

```

```{toctree}
:maxdepth: 2
:caption: Development
api/index

contribute

```
