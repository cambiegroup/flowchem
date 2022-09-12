# Add a new device to flowchem

![New device meme](./images/new-device-type.jpg)

If you want to add support for a new device-type this is tha page for you!
Let's assume you got a new lab device, an _✨Extendable Ear✨_ manufactured by _Weasley & Weasley_.
And of course you want to control it via flowchem. Solid idea!👏

## Code
In the `flowchem.device` subpackage, the device modules are organized in folders by manufacturer.
Since this is the first device from _Weasley & Weasley_ in flowchem, we need to create a new folder under
`/flowchem/devices`. Let's call it `/flowchem/devices/Weasley` to avoid the use of special characters ;)

In this folder we will write a _module_ (i.e. a python file 🐍) called `ExtendableEar.py` to control our magic device.
We create it piece by piece, but the content of the module will look like this:

```python
from flowchem.models.base_device import BaseDevice


class ExtendeableEar(BaseDevice):
    """Our virtual Extendable Ear!"""

    def __init__(self):
        ...

```



```python
from fastapi import APIRouter
from flowchem.models.base_device import BaseDevice


class ExtendeableEar(BaseDevice):
    """Our virtual Extendable Ear!"""

    def __init__(self):
        ...

    async def initialize(self):
        ...

    async def deploy(self):
        ...

    async def listen_for(self, seconds: str):
        ...

    async def retract(self):
        ...

    def get_router(self) -> APIRouter:
        ...

```
- instantiable from dict or if not possible with from_config @classmethod

Finally, add to __init__.py to ensure it is available for import with a statement like
```python
from flowchem.devices import ExtendableEar
```


## Documentation
Write a brief description of the class you created in the /docs/devices/ folder, following the same manufacturer-base hierarchy.
Ideally manufacturer communication manual is added to the docs

:::{note}
This is an implementation detail that user do not have to care about since the `flowchem.device` submodules will hide
this nested layer via thier `__init__.py`. If you do not understand what this means it is not important, and you can
safely skip this note if you follow this guide.
:::
