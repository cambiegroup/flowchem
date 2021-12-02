import nox


@nox.session(python=['3.9', '3.10'])
def tests(session):
    session.install('pytest', 'pytest-asyncio', 'pytest-cov')
    session.install('.')
    session.run('pytest')


@nox.session
def lint(session):
    session.install('flake8')
    session.run('flake8', '.', '--count', '--select=E9,F63,F7,F82', '--show-source', '--statistics')


@nox.session
def type_check(session):
    session.install('mypy')
    session.run('mypy', '--install-types', '--non-interactive', '--python-version 3.9', 'flowchem')
