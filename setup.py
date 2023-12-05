from setuptools import setup, find_packages

setup(
    name='flowchem',
    version='1.0.0a3',
    description="Provides commands for SparkHolland devices support in flowchem.",
    author='Jakob Wolf',
    author_email="75418671+JB-Wolf@users.noreply.github.com",
    packages=find_packages(where="src"),
    package_dir = {"": "src"},
    install_requires=[
    ],
)
