import asyncio
import warnings
from pathlib import Path
import ctypes.wintypes
from typing import Union


def get_my_docs_path():
    """
    Spinsolve control software is only available on Windows, so lack of cross-platform support is unavoidable.
    XSD and XML schema are installed in my documents, whose location, if custom, can be obtained as follows.
    """
    # From https://stackoverflow.com/questions/6227590
    CSIDL_PERSONAL = 5       # My Documents
    SHGFP_TYPE_CURRENT = 0   # Get current, not default value
    buf= ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
    return Path(buf.value)


def create_folder_mapper(remote_root: Path, local_root: Path) -> callable:
    """
    Returns a function that converts path relative to remote_root to their corresponding on local_root
    Used when using spinsolve on a remote PC to share the result data via a remotely mounted network drive
    """
    def folder_mapper(path_to_be_translated: Union[Path, str]):
        """
        Given a remote path converts it to the corresponding local location, or None + warning if not possible.
        """
        # Ensures it is a Path object
        if isinstance(path_to_be_translated, str):
            path_to_be_translated = Path(path_to_be_translated)

        nonlocal remote_root, local_root
        # If relative translate if not error
        if path_to_be_translated.is_relative_to(remote_root):
            suffix = path_to_be_translated.relative_to(remote_root)
            return local_root / suffix
        else:
            warnings.warn(f"Cannot translate remote path {path_to_be_translated} to a local path!"
                          f"{path_to_be_translated} is not relative to {remote_root}")
    return folder_mapper


async def get_streams_for_connection(host, port) -> (asyncio.StreamReader, asyncio.StreamWriter):
    """
    Given a target (host, port) returns the corresponding asyncio streams (I/O).
    """
    try:
        read, write = await asyncio.open_connection(host, port)
    except Exception as e:
        raise ConnectionError(f"Error connecting to {host}:{port} -- {e}") from e
    return read, write


def run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()