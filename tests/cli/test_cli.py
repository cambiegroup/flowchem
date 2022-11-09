from textwrap import dedent

from click.testing import CliRunner

from flowchem.__main__ import main


def test_cli(mocker):
    runner = CliRunner()
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
