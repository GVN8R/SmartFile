"""High-performance folder scanning utilities for SmartFile."""

import os
import pathlib
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


def _scan_directory(directory_path):
    """Collect files and subdirectories from one directory."""
    files = []
    subdirectories = []

    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                entry_path = pathlib.Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    subdirectories.append(entry_path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(entry_path)
    except OSError:
        return files, subdirectories

    return files, subdirectories


def scan_folder(folder_path, max_workers=None):
    """Recursively scan a folder for files using a small thread pool."""
    
    # Get filepath
    root_dir = pathlib.Path(folder_path)
    if not root_dir.exists() or not root_dir.is_dir():
        return []

    # Use between 4 and 32 workers
    if max_workers is None:
        max_workers = min(32, max(4, (os.cpu_count() or 1) * 2))

    file_dir_list = []
    pending = set()

    # Get all files and subdirectories in the selected folder and return the list
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pending.add(executor.submit(_scan_directory, root_dir))

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                files, subdirectories = future.result()
                file_dir_list.extend(files)

                for directory in subdirectories:
                    pending.add(executor.submit(_scan_directory, directory))

    return file_dir_list