import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="flowchem",
    version="0.1.0",
    author="Dario Cambie, Jakob Wolf",
    author_email="dario.cambie@mpikg.mpg.de, jakob.wolf@mpikg.mpg.de",
    description="Misc utilities for flow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cambiegroup/flowchem",
    packages=setuptools.find_packages(),
    install_requires=['pyserial', 'pyserial-asyncio', 'pint', 'pandas', 'numpy'],
    python_requires='>=3.6',
)