# Design principles

Principles:
- Follows unix philosophy: do one thing, and do it well. Flowchem provides uniform API endpoints for device connection.
- Abstracts away the myriads of different underlying hardware connections methods.
- No-code shim: device settings via YAML file creates OpenAPI endpoints with predictable names based on serial numbers.
- Implements existing interoperable standard for lab IoT to avoid standard proliferation.
- Long-term vision is that each device comes with its own web interface following this standard.

Implementation design:
- intended use via CLI endpoint, installed via `pipex`.
- Ideally, failure in one device should not affect the others. (Catch-all error via starlette middleware SO 61596911)
- to ease debug, add support for auto-reload if settings file is changed. (easy, need to trigger reload on changes, via watchfiles)
- only connection specific settings are needed. Device-specific are optional on instantiation even if needed for use.
  - This e.g. a syringe pump might need syringe diameter and volume before use, but those are device specific parameters and not connection specific, so they are not required in flowchem config.
  - ideally all permanent device specific parameters (not changing during normal use) are received/set in a uniform way and advertised as such (to enabling dynamic graphs config via web interface, somehow similar to Magritek protocol options).
- Don't force code-reuse, but allow for easy extension and leave device modules as independent as possible.
- Each device module should be accompanied by tests and documentation/examples.
- Following abstract device ontologies ease abstraction in higher level code.
- Each device MUST have a name, unique per server, tha will be the endpoint path.  If Non will be generated.
  - If a unique name can be programmatically used after init (e.g. based on SERIAL_NUMBER), than that will be also advertised in autodiscover name.
  - This allows dependent libraries to use static names even though they are not yet known at flowchem init.

Inspired by many packages with similar aims, including (in alphabetical order):
- [Chemios](https://github.com/Chemios/chemios)
- [ChemOS](https://github.com/aspuru-guzik-group/ChemOS)
- [MechWolf](https://github.com/MechWolf/MechWolf)
- [Octopus](https://github.com/richardingham/octopus)
