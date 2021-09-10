from flowchem.cli import main


def test_main(capsys):
    main()
    stdout, errout = capsys.readouterr()
    assert "Here" in stdout
