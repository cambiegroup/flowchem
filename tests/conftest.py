import sys
from pathlib import Path

import pytest
from xprocess import ProcessStarter


@pytest.fixture(scope="module")
def flowchem_test_instance(xprocess):
    config_file = Path(__file__).parent.resolve() / "test_config.toml"
    main = Path(__file__).parent.resolve() / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    yield
    xprocess.getinfo("flowchem_instance").terminate()
