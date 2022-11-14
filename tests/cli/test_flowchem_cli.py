from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner

from flowchem.__main__ import main


def test_cli(mocker):
    runner = CliRunner()
    # Skip running server
    mocker.patch("uvicorn.run", return_value=None)

    with runner.isolated_filesystem():
        with open("test_configuration.toml", "w") as f:
            f.write(
                dedent(
                    """[device.test-device]\n
            type = "FakeDevice"\n"""
                )
            )

        result = runner.invoke(main, ["test_configuration.toml"])
        assert result.exit_code == 0

        result = runner.invoke(
            main, ["test_configuration.toml", "--log", "logfile.log"]
        )
        assert result.exit_code == 0
        assert Path("logfile.log").exists()
        assert "Starting server" in Path("logfile.log").read_text()
