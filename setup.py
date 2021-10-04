import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="flowchem",
    version="0.0.2.post1",
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
        "opcua",
        "asyncua",
        "phidget22",
        "getmac",
        "lmfit",
        "nmrglue",
    ],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["flowchem=flowchem.cli:main"]},
)
