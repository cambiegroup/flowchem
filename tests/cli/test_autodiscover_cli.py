import pytest
from click.testing import CliRunner

from flowchem.utils.autodiscover import main


@pytest.mark.skip(reason="Fails in CI due to network limits on broadcast")
def test_autodiscover_cli(mocker):
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ["--assume-yes", "--safe"],
        )
        assert result.exit_code == 0
