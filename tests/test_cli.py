""" CLI should be used for device tree initialization from config. """
from flowchem.cli import main


def test_main(capsys):
    """ Stub for CLI entrypoint """
    main()
    stdout, errout = capsys.readouterr()
    assert "Here" in stdout
