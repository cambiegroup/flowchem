import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

def get_version(rel_path: str) -> str:
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            # __version__ = "0.9"
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")

setuptools.setup(
    name="flowchem",
    version=get_version("flowchem/__init__.py"),
    author="Dario Cambié, Jakob Wolf",
    author_email="dario.cambie@mpikg.mpg.de, jakob.wolf@mpikg.mpg.de",
    description="Flowchem is a python library to control a variety of instruments commonly found in chemistry labs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cambiegroup/flowchem",
    packages=setuptools.find_packages(),
    install_requires=[
        "pyserial",
        "pyserial-asyncio",
        "pint",
        "pandas",
        "scipy",
        "numpy",
        "asyncua",
        "phidget22",
        "getmac",
        "lmfit",
        "nmrglue",
    ],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["flowchem=flowchem.cli:main"]},
)
