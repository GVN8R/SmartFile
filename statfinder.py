"""Statistics and size-formatting helpers for analyzing folders."""

import os


def human_readable_size(size):
    """Convert a size in bytes to a human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}PB"


def get_folder_stats(path, largest_count=10):
    """Collect disk usage statistics for a folder."""
    total_size = 0
    file_count = 0
    dir_count = 0
    largest_files = []

    for root, dirs, files in os.walk(path):
        dir_count += len(dirs)
        for file_name in files:
            file_count += 1
            file_path = os.path.join(root, file_name)
            try:
                size = os.path.getsize(file_path)
            except OSError:
                continue
            total_size += size
            largest_files.append((size, file_path))

    largest_files.sort(reverse=True, key=lambda item: item[0])
    largest_files = largest_files[:largest_count]

    return {
        "path": path,
        "total_files": file_count,
        "total_directories": dir_count,
        "total_size_bytes": total_size,
        "total_size": human_readable_size(total_size),
        "average_file_size": human_readable_size(total_size / file_count) if file_count else "0B",
        "largest_files": largest_files,
    }


def show_folder_disk_usage(path, largest_count=10):
    """Print statistics about disk usage for a particular folder."""
    stats = get_folder_stats(path, largest_count)

    print(f"Folder: {stats['path']}")
    print(f"Total files: {stats['total_files']}")
    print(f"Total directories: {stats['total_directories']}")
    print(f"Total size: {stats['total_size']} ({stats['total_size_bytes']} bytes)")
    print(f"Average file size: {stats['average_file_size']}")
    print(f"Top {len(stats['largest_files'])} largest files:")
    for size, file_path in stats['largest_files']:
        print(f"  {human_readable_size(size)}\t{file_path}")
