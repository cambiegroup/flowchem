# Injection Valve

The injection valve model represents any valve with two positions: `LOAD` and `INJECT`.

The typical example is a 6-ports-2-positions valve commonly used for HPLC sample injection.
Example devices are

```{eval-rst}
.. autoclass:: flowchem.models.valves.injection_valve.InjectionValve
    :show-inheritance:
    :members:
    :exclude-members: get_router, initialize
    :special-members: __init__
```
