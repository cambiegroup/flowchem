from io import BytesIO
from textwrap import dedent

import pytest
from flowchem_test.fakedevice import FakeDevice

from flowchem.server.configuration_parser import parse_config
from flowchem.utils.exceptions import InvalidConfiguration


def test_minimal_valid_config():
    cfg_txt = BytesIO(
        dedent(
            """
            [device.test-device]
            type = "FakeDevice"
            """,
        ).encode("utf-8"),
    )
    cfg = parse_config(cfg_txt)
    assert "filename" in cfg
    assert "device" in cfg
    assert isinstance(cfg["device"].pop(), FakeDevice)


def test_name_too_long():
    cfg_txt = BytesIO(b"""[device.this_name_is_too_long_and_should_be_shorter]""")
    with pytest.raises(InvalidConfiguration) as excinfo:
        parse_config(cfg_txt)
    assert "too long" in str(excinfo.value)
