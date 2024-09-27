import sys
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest
import time


# pytest tests/devices/valve/test_knauer.py -s
# pytest ./tests -m Knauer_Distribution_Valve -s

@pytest.fixture(scope="module")
def api_dev(xprocess):
    config_file = Path(__file__).parent.resolve() / "knauer.toml"
    main = Path(__file__).parent.resolve() / ".." / ".." / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    yield get_all_flowchem_devices()
    xprocess.getinfo("flowchem_instance").terminate()


@pytest.mark.Knauer_Distribution_Valve
def test_set_get_monitor_position(api_dev):
    """Test the set_monitor_position method."""
    valve = api_dev['test']['distribution-valve']
    valve.put("monitor_position", params={"position": "2"})
    time.sleep(2)
    position = valve.get("monitor_position").json()
    time.sleep(1)
    assert position == "2", "The set position does not working"


@pytest.mark.Knauer_Distribution_Valve
def test_set_get_position(api_dev):
    """Test the set_position method """
    valve = api_dev['test']['distribution-valve']
    valve.put("position", params={"connect": "[[1, 0]]"})
    time.sleep(2)
    pos = valve.get("position").json()
    assert pos == [[1, 0]], "The set and get position do not worked."
