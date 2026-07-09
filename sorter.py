"""File categorization and organization helpers for SmartFile."""

import shutil
import pathlib

# File categories and their respectiv
CATEGORY_FOLDERS = {
    "text": "Documents",
    "data": "Documents",
    "audio": "Music",
    "video": "Videos",
    "3dimage": "3D",
    "rasterimage": "Images",
    "vectorimage": "Images",
    "pagelayout": "Documents",
    "spreadsheet": "Documents",
    "database": "Data",
    "executable": "Applications",
    "game": "Games",
    "cad": "CAD",
    "gis": "GIS",
    "web": "Web",
    "plugin": "Plugins",
    "font": "Fonts",
    "system": "System",
    "settings": "Settings",
    "encoded": "Archives",
    "compressed": "Archives",
    "diskimage": "Images",
    "developer": "Developer",
    "backup": "Backups",
    "other": "Other",
}


def _build_extension_lookup():
    extension_groups = {
        "text": ['.doc', '.docx', '.eml', '.msg', '.odt', '.pages', '.rtf', '.tex', '.txt', '.wpd'],
        "data": ['.aae', '.csv', '.dat', '.key', '.log', '.mpp', '.obb', '.ppt', '.pptx', '.rpt', '.tar', '.vcf', '.xml'],
        "audio": ['.aif', '.flac', '.m3u', '.m4a', '.mid', '.mp3', '.ogg', '.wav', '.wma'],
        "video": ['.3gp', '.asf', '.avi', '.flv', '.m4v', '.mov', '.mp4', '.mpg', '.swf', '.ts', '.vob', '.wmv'],
        "3dimage": ['.3dm', '.3ds', '.blend', '.dae', '.fbx', '.max', '.obj'],
        "rasterimage": ['.bmp', '.dcm', '.dds', '.djvu', '.gif', '.heic', '.jpg', '.png', '.psd', '.tga', '.tif'],
        "vectorimage": ['.ai', '.cdr', '.emf', '.eps', '.ps', '.sketch', '.svg', '.vsdx'],
        "pagelayout": ['.indd', '.oxps', '.pdf', '.pmd', '.pub', '.qxp', '.xps'],
        "spreadsheet": ['.numbers', '.ods', '.xlr', '.xls', '.xlsx'],
        "database": ['.accdb', '.crypt14', '.db', '.mdb', '.odb', '.pdb', '.sql', '.sqlite'],
        "executable": ['.apk', '.app', '.bat', '.cmd', '.com', '.exe', '.ipa', '.jar', '.run', '.sh'],
        "game": ['.dem', '.gam', '.gba', '.nes', '.pak', '.rom', '.sav'],
        "cad": ['.dgn', '.dwg', '.dxf', '.step', '.stl', '.stp'],
        "gis": ['.gpx', '.kml', '.kmz', '.osm'],
        "web": ['.asp', '.aspx', '.cer', '.cfm', '.csr', '.css', '.html', '.js', '.json', '.jsp', '.php', '.xhtml'],
        "plugin": ['.crx', '.ecf', '.plugin', '.safariextz', '.xpi'],
        "font": ['.fnt', '.otf', '.ttf', '.woff', '.woff2'],
        "system": ['.ani', '.cab', '.cpl', '.cur', '.deskthemepack', '.dll', '.dmp', '.drv', '.icns', '.ico', '.lnk', '.reg', '.sys'],
        "settings": ['.cfg', '.ini', '.pkg', '.set'],
        "encoded": ['.asc', '.enc', '.mim', '.uue'],
        "compressed": ['.7z', '.cbr', '.deb', '.gz', '.rar', '.rpm', '.xapk', '.zip', '.zipx'],
        "diskimage": ['.dmg', '.img', '.iso', '.mdf', '.vcd'],
        "developer": ['.appx', '.c', '.class', '.config', '.cpp', '.cs', '.h', '.java', '.kt', '.lua', '.m', '.md', '.pl', '.py', '.sb3', '.sln', '.swift', '.uasset','.unity', '.vb', '.vcxproj', '.xcodeproj', '.yml'],
        "backup": ['.abk', '.arc', '.bak', '.tmp'],
    }

    extension_to_category = {}
    for category, extensions in extension_groups.items():
        for extension in extensions:
            extension_to_category.setdefault(extension.lower(), category)

    return extension_to_category


extension_to_category = _build_extension_lookup()


def sort_files(file_dir_list):
    type_lookup = {"text": [], "data": [], "audio": [],
                   "video": [], "3dimage": [], "rasterimage": [],
                   "vectorimage": [], "pagelayout": [],
                   "spreadsheet": [], "database": [],
                   "executable": [], "game": [], 'cad': [],
                   "gis": [], "web": [], "plugin": [],
                   "font": [], "system": [], "settings": [],
                   "encoded": [], "compressed": [],
                   "diskimage": [], "developer": [],
                   'backup': [], "other": []}

    for file in file_dir_list:
        suffix = file.suffix.lower()
        category = extension_to_category.get(suffix, 'other')
        type_lookup[category].append(file)

    return type_lookup


def organize_files(source_folder, destination_folder, move_files=False):
    """Copy or move files from a source folder into category-based subfolders."""
    source_path = pathlib.Path(source_folder)
    destination_path = pathlib.Path(destination_folder)

    if not source_path.exists() or not source_path.is_dir():
        raise ValueError("Source folder does not exist or is not a directory")

    destination_path.mkdir(parents=True, exist_ok=True)

    files = [path for path in source_path.rglob('*') if path.is_file()]
    organized = []

    for file_path in files:
        category = None
        suffix = file_path.suffix.lower()
        for ext, cat in extension_to_category.items():
            if suffix == ext:
                category = cat
                break
        if category is None:
            category = "other"

        target_folder = destination_path / CATEGORY_FOLDERS.get(category, "Other")
        target_folder.mkdir(parents=True, exist_ok=True)
        target_path = target_folder / file_path.name

        if target_path.exists():
            counter = 1
            while target_path.exists():
                target_path = target_folder / f"{file_path.stem}_{counter}{file_path.suffix}"
                counter += 1

        if move_files:
            shutil.move(str(file_path), str(target_path))
        else:
            shutil.copy2(str(file_path), str(target_path))

        organized.append((file_path, target_path))

    return organized