# Tests

The tests are meant to be run with `pytest`.

All the test that do *not* require access to any hardware device are automatically run for every pull request against
the main branch.

Additional device-specific test can be run with the corresponding marker (e.g. `pytest -m Spinsolve`)
