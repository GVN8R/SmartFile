"""Duplicate-file detection helpers for the SmartFile analyzer."""

import hashlib
import pathlib


def _hash_file(path: pathlib.Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file incrementally in chunks to reduce memory usage."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate_files(file_lookup: dict[str, list[pathlib.Path]]) -> list[list[pathlib.Path]]:
    """Return groups of duplicate files from a mapping of category to file paths."""
    file_groups: dict[str, list[pathlib.Path]] = {}

    for _, paths in file_lookup.items():
        for path in paths:
            candidate = pathlib.Path(path)
            if not candidate.exists() or not candidate.is_file():
                continue

            digest = _hash_file(candidate)
            file_groups.setdefault(digest, []).append(candidate)

    return [paths for paths in file_groups.values() if len(paths) > 1]
