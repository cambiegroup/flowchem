import pytest
from click.testing import CliRunner

from flowchem.autodiscover import main


@pytest.mark.skip(reason="This blocks CI, works locally though.")
def test_cli(mocker):
    runner = CliRunner()
    mocker.patch("uvicorn.run", return_value=None)

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "--assume-yes",
            ],
        )
        assert result.exit_code == 0
