from click.testing import CliRunner

from flowchem.autodiscover import main


def test_cli(mocker):
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ["--assume-yes", "--safe"],
        )
        assert result.exit_code == 0
