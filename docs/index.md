Flowchem documentation
======================


Flowchem is a library to control instruments and devices commonly found in chemistry labs
via an interoperable web API.

Lear more about [how flowchem works](./learning/index.md).

::::{grid} 1 2 3 3

:::{grid-item}
:columns: auto

```{button-ref} getting_started
:color: primary
```
:::

:::{grid-item}
:columns: auto

```{button-ref} Tutorial
:color: secondary
```
:::

:::{grid-item}
:columns: auto

```{button-ref} Examples
:color: secondary
```
:::
::::
---

## Install flowchem
To install `flowchem`, ensure you have Python installed, then run:
```shell
pip install flowchem
```
or install it with `pipx`:
```shell
pip install pipx
pipx ensurepath
pipx install flowchem
```
Read more about [installing flowchem](./getting_started.md).

---

## Tutorial
View the [Simple Reactor Control Tutorial]() for a hands-on introduction to flowchem:
```toml
[device.example1]
type="FakeDevice"
```
```{button-ref} ./examples/hallo-world
:color: primary
```
---

## Citation
If you use flowchem for your paper, please remember to cite it!

[//]: # (TODO: add ref to paper once out)

```{toctree}
:maxdepth: 2
:hidden:

getting_started

learning/index

devices/supported_devices

api/index

contribute

add_device/index

```
