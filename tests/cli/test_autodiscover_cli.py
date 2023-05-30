import pytest
import os
from click.testing import CliRunner

from flowchem.utils.autodiscover import main


IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.mark.skipif(
    IN_GITHUB_ACTIONS,
    reason="Test doesn't work in Github Actions since broadcast is not allowed.",
)
def test_autodiscover_cli():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ["--assume-yes", "--safe"],
        )
        assert result.exit_code == 0
