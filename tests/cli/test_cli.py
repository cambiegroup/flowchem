from click.testing import CliRunner
from flowchem.cli import main


def test_cli():
    runner = CliRunner()
    result = runner.invoke(main, ["test_configuration.toml"])
    assert result.exit_code == 0
