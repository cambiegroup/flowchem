import sys
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest

# pytest tests/devices/Fake_group/test_fakedevice.py -s
# pytest ./tests -m FakeDevice -s

@pytest.fixture(scope="module")
def api_dev(xprocess):

    config_file = Path(__file__).parent.resolve() / "fakedevice.toml"
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


@pytest.mark.FakeDevice
def test_fakedevice(api_dev):
    component = api_dev['test']['FakeComponent']
    assert component.put("set_specif_command", params={"parameter_1": "first", "parameter_2": "second"})
    #msg = ("This message is an example of a test to interact with the user while he/she is running the\n"
    #       "test. It is crucial that the user gives some feedback about the devices, especially in cases\n"
    #       "of devices with mobile parts such as pumps/valves. In some cases, such as sensors, it can be\n"
    #       "important to have a reference answer to compare with. This stage of the test is important to\n"
    #       "simulate/perform a hardware test.\n"
    #       "Answer this, just as an example: Is the sky blue? (yes/no):")
    #response = input(msg)
    #assert response.lower() == 'yes', "The user indicated that the sky is not blue."


@pytest.mark.FakeDevice
def test_fake_receive_data(api_dev):
    component = api_dev['test']['FakeComponent']
    result = component.get("fake_receive_data").text
    assert float(result) == 0.5


