# Devices

The following devices are currently supported in flowchem:

| Manufacturer     | Device / Model     | `flowchem` name   | `flowchem`  components              | Auto-discoverable |
|------------------|--------------------|-------------------|-------------------------------------|:-----------------:|
| DataApex         | Clarity            | Clarity           | HPLCControl                         |        NO         |
| Hamilton         | ML600              | ML600             | SyringePump, DistributionValve      |        YES        |
| HarvardApparatus | Elite11            | Elite11           | SyringePump                         |        YES        |
| Huber            | various            | HuberChiller      | TemperatureControl                  |        YES        |
| Knauer           | Azura Compact      | AzuraCompact      | HPLCPump, PressureSensor            |        YES        |
| Knauer           | V 2.1S             | KnauerValve       | InjectionValve or DistributionValve |        YES        |
| Magritek         | Spinsolve          | Spinsolve         | NMRControl                          |        NO         |
| Manson           | HCS-3102 family    | MansonPowerSupply | PowerSupply                         |        NO         |
| Mettler Toledo   | iCIR               | FlowIR            | IRControl                           |        NO         |
| Phidgets         | VINT               | PressureSensor    | PressureSensor                      |        NO         |
| Vici Valco       | Universal Actuator | ViciValve         | InjectionValve                      |        NO         |


```{toctree}
:maxdepth: 1
:caption: Devices

dataapex/clarity
hamilton/ml600
harvardapparatus/elite11
huber/chiller
knauer/azura_compact
knauer/valves
magritek/spinsolve
manson/manson
mettler/flowir
phidgets/p_sensor
vicivalco/vicivalve

```
