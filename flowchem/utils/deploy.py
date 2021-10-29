""" Util function to install dependencies on PC with no internet access. """
import argparse
from pathlib import Path
import subprocess
import sys

EXCHANGE_FOLDER = Path(r"W:\BS-FlowChemistry\Resources\python_packages_local")


def install_from_folder(package: str, folder: Path):
    """ pip-install packages locally available in a folder. """
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            f"--find-links={folder.as_posix()}",
            package,
        ]
    )


def download_to_folder(package: str, folder: Path):
    """ pip-download packages to a local folder. """
    subprocess.check_call(
        [sys.executable, "-m", "pip", "download", package, "-d", folder.as_posix()]
    )


def get_package_list():
    """ Return the list of packages to download/install from the requirements file """
    req_file = Path("../../requirements.txt")

    package = []

    with req_file.open() as fh:
        lines = fh.readlines()
        for line in lines:
            # Ignore nmrglue
            if "nmrglue" in line:
                continue

            package.append(line.split("~=")[0])

    return package


def download_all():
    """ Downloads all packages in requirements. """
    for package in get_package_list():
        download_to_folder(package, EXCHANGE_FOLDER)
        print(f"Downloaded {package} to {EXCHANGE_FOLDER.as_posix()}")


def install_all():
    """ Installs all packages in requirements. """
    for package in get_package_list():
        install_from_folder(package, EXCHANGE_FOLDER)
        print(f"Installed {package} from {EXCHANGE_FOLDER.as_posix()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", help="Download packages", action="store_true")
    parser.add_argument("--install", help="Install packages", action="store_true")
    args = parser.parse_args()
    if args.download:
        download_all()
    elif args.install:
        install_all()
    else:
        print("Nothing to do! either download or install!")
