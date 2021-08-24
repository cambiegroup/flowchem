# flowchem
A collection of utilities and script for flow chemistry labs.

Concepts:
- device should only raise exception on creation. That's reasonable and most likely won't impact the experiment to be performed (i.e. fail fast approach).
  - it follows that the connection to the device is implicit in the object instantiation
  - communication streams are passed to the device constructors (i.e. dependency injection). This greatly simplify testing, removing the need to mantain monkey patches.
  - every device driver should be accompanied by tests and documentation (at least in form of examples).
- device should be lenient with errors in API usage but still warn the user if the intended action has not been performed (hinting why).
- all device should use generic flowchem.exceptions or sublcass of those for custom exceptions.