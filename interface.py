"""Tkinter-based desktop interface for scanning, analyzing, and previewing files."""

import json
import math
import os
import shutil
import subprocess
import threading
import tkinter as tk
import wave
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageOps, ImageTk

import duplicatefinder
import scanner
import sorter
import statfinder


def analyze_folder(folder_path, progress_callback=None):
    """Scan a folder, sort files into categories, find duplicates, and collect disk stats."""
    
    # Raise error if folder hasn't been selected
    if not folder_path:
        raise ValueError("Please choose a folder first.")

    # Set progress bar as more parts of the function are completed
    if progress_callback:
        progress_callback("Scanning files...", 0.1)
    file_dir_list = scanner.scan_folder(folder_path)

    if progress_callback:
        progress_callback("Sorting files...", 0.35)
    type_lookup = sorter.sort_files(file_dir_list)

    if progress_callback:
        progress_callback("Finding duplicates...", 0.75)
    duplicates = duplicatefinder.find_duplicate_files(type_lookup)

    if progress_callback:
        progress_callback("Gathering disk usage...", 0.95)
    stats = statfinder.get_folder_stats(folder_path)

    if progress_callback:
        progress_callback("Analysis complete", 1.0)

    # Get file categories
    categories = {name: len(paths) for name, paths in type_lookup.items()}

    # return sets of data
    return {
        "folder": folder_path,
        "files": file_dir_list,
        "categories": categories,
        "duplicates": duplicates,
        "stats": stats,
        "type_lookup": type_lookup,
    }


def draw_pie_chart(canvas, categories):
    """Draw a simple pie chart for the provided category counts."""
    values = [count for count in categories.values() if count > 0]
    labels = [name for name, count in categories.items() if count > 0]
    if not values:
        canvas.delete("all")
        canvas.create_text(120, 120, text="No data", anchor="center")
        return

    colors = [
        "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#EECA3B",
        "#B279A2", "#FF9DA7", "#9D755D", "#BAB0AC", "#79706E", "#D4A6C8"
    ]

    canvas.delete("all")
    center_x = 100
    center_y = 100
    radius = 75
    start_angle = 0

    total = sum(values)
    for index, value in enumerate(values):
        angle = (value / total) * 360
        end_angle = start_angle + angle
        color = colors[index % len(colors)]
        canvas.create_arc(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            start=start_angle,
            extent=angle,
            fill=color,
            outline="white",
            width=1,
        )
        start_angle = end_angle

    for index, label in enumerate(labels):
        x = 190 + (index % 2) * 120
        y = 20 + (index // 2) * 14
        color = colors[index % len(colors)]
        canvas.create_rectangle(x, y, x + 10, y + 10, fill=color, outline="")
        canvas.create_text(x + 14, y + 5, text=f"{label}: {values[index]}", anchor="w", font=("Segoe UI", 7))


def draw_storage_chart(canvas, result):
    """Draw a simple storage-usage chart using file sizes from the analysis result."""
    category_sizes = {}
    for category, files in result.get("type_lookup", {}).items():
        total_size = 0
        for file_path in files:
            try:
                total_size += os.path.getsize(file_path)
            except OSError:
                continue
        if total_size > 0:
            category_sizes[category] = total_size

    values = list(category_sizes.values())
    labels = list(category_sizes.keys())
    if not values:
        canvas.delete("all")
        canvas.create_text(140, 140, text="No storage data", anchor="center")
        return

    colors = [
        "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#EECA3B",
        "#B279A2", "#FF9DA7", "#9D755D", "#BAB0AC", "#79706E", "#D4A6C8"
    ]

    canvas.delete("all")
    center_x = 100
    center_y = 100
    radius = 75
    start_angle = 0

    total = sum(values)
    for index, value in enumerate(values):
        angle = (value / total) * 360
        end_angle = start_angle + angle
        color = colors[index % len(colors)]
        canvas.create_arc(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            start=start_angle,
            extent=angle,
            fill=color,
            outline="white",
            width=1,
        )
        start_angle = end_angle

    for index, label in enumerate(labels):
        x = 190 + (index % 2) * 120
        y = 20 + (index // 2) * 14
        color = colors[index % len(colors)]
        canvas.create_rectangle(x, y, x + 10, y + 10, fill=color, outline="")
        canvas.create_text(x + 14, y + 5, text=f"{label}: {statfinder.human_readable_size(values[index])}", anchor="w", font=("Segoe UI", 7))


def is_supported_image_path(path):
    """Return True when Pillow can open the file as an image."""
    try:
        with Image.open(path) as image:
            image.load()
        return True
    except Exception:
        return False


def format_duration(seconds):
    """Format seconds into a human-readable duration string."""
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def get_media_duration(path):
    """Try to read the duration of an audio or video file using ffprobe, mutagen, or a WAV header fallback."""
    path = str(path)
    extension = os.path.splitext(path)[1].lower()

    if extension == ".wav":
        try:
            with wave.open(path, "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                if rate:
                    return format_duration(frames / float(rate))
        except Exception:
            pass

    try:
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            cmd = [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                return format_duration(float(result.stdout.strip()))
    except Exception:
        pass

    try:
        from mutagen import File

        media = File(path)
        if media and getattr(media, "info", None) and getattr(media.info, "length", None):
            return format_duration(float(media.info.length))
    except Exception:
        pass

    return None


def get_image_files(result):
    """Collect image files discovered during the analysis."""
    image_paths = []
    if not result:
        return image_paths

    for files in result.get("type_lookup", {}).values():
        for file_path in files:
            if os.path.exists(file_path) and is_supported_image_path(file_path):
                image_paths.append(file_path)
    return image_paths


def get_media_files(result):
    """Collect audio and video files discovered during the analysis."""
    media_paths = []
    if not result:
        return media_paths

    media_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.mp4', '.mkv', '.mov', '.avi', '.wmv', '.webm', '.m4v'}
    for files in result.get("type_lookup", {}).values():
        for file_path in files:
            if os.path.exists(file_path) and os.path.splitext(str(file_path))[1].lower() in media_extensions:
                media_paths.append(file_path)
    return media_paths


def get_preview_files(result):
    """Collect image and media files discovered during the analysis."""
    preview_paths = []
    if not result:
        return preview_paths

    for file_path in get_image_files(result):
        preview_paths.append(file_path)
    for file_path in get_media_files(result):
        preview_paths.append(file_path)
    return preview_paths


def filter_preview_files(preview_paths, query):
    """Filter previewable files by a search query."""
    if not query:
        return preview_paths

    needle = query.strip().lower()
    if not needle:
        return preview_paths

    return [path for path in preview_paths if needle in os.path.basename(str(path)).lower() or needle in str(path).lower()]


def populate_selector(selector, variable, values):
    """Populate a combobox with preview options."""
    if values:
        selector.config(values=values)
        selector.config(state="readonly")
        if variable.get() not in values:
            variable.set(values[0])
    else:
        selector.config(values=[])
        variable.set("")
        selector.config(state="disabled")


def show_preview(result, canvas, label, preview_var=None, preview_selector=None, search_query=""):
    """Show a preview for the selected image or a duration for audio/video files."""
    
    # Only show previews if report is complete
    if not result:
        canvas.delete("all")
        label.config(text="No preview data")
        canvas.create_text(120, 90, text="No preview available", anchor="center")
        return

    # Change file depending on search bar contents
    preview_paths = filter_preview_files(get_preview_files(result), search_query)
    preview_values = [str(path) for path in preview_paths]
    populate_selector(preview_selector, preview_var, preview_values)

    selected_path = preview_var.get() if preview_var is not None else ""
    preview_path = None
    if selected_path:
        for path in preview_paths:
            if str(path) == selected_path:
                preview_path = path
                break
    if preview_path is None and preview_paths:
        preview_path = preview_paths[0]

    # Checks if there is no file selected
    canvas.delete("all")
    if not preview_path or not os.path.exists(preview_path):
        label.config(text="No preview selected")
        canvas.create_text(120, 90, text="No preview available", anchor="center")
        return

    # Gets the file extension and checks if it's a media file
    extension = os.path.splitext(str(preview_path))[1].lower()
    is_media = extension in {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.mp4', '.mkv', '.mov', '.avi', '.wmv', '.webm', '.m4v'}

    # If file is media, get duration and display
    if is_media:
        duration = get_media_duration(preview_path)
        label.config(text=f"Media: {os.path.basename(str(preview_path))} - {duration or 'duration unavailable'}")
        canvas.create_text(120, 90, text=f"Audio/Video file\n{duration or 'Duration unavailable'}", anchor="center")
        return
    
    # Attempt to open and view image files
    try:
        with Image.open(preview_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((220, 160))
            if image.mode in {"RGBA", "LA", "P", "1"}:
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")
            photo = ImageTk.PhotoImage(image)
            canvas.create_image(120, 90, image=photo)
            canvas.image = photo
            label.config(text=f"Preview: {os.path.basename(str(preview_path))}")
    except Exception:
        label.config(text="Preview unavailable")
        canvas.create_text(120, 90, text="Preview unavailable", anchor="center")


def get_favorites_file():
    """Return the path used to store favorite folders."""
    return os.path.join(os.path.dirname(__file__), "favorites.json")


def load_favorites():
    """Load saved favorite folders from disk."""
    favorites_file = get_favorites_file()
    if not os.path.exists(favorites_file):
        return []

    try:
        with open(favorites_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return [folder for folder in data if isinstance(folder, str) and os.path.isdir(folder)]
    except Exception:
        return []

    return []


def save_favorites(favorites):
    """Persist favorite folders to disk."""
    favorites_file = get_favorites_file()
    try:
        with open(favorites_file, "w", encoding="utf-8") as handle:
            json.dump(favorites, handle)
    except Exception:
        pass


def add_favorite_folder(folder_path):
    """Add a folder to the favorites list if it is not already present."""
    if not folder_path:
        return []

    normalized = os.path.abspath(folder_path)
    favorites = [folder for folder in load_favorites() if os.path.isdir(folder)]
    if normalized not in favorites:
        favorites.insert(0, normalized)
    save_favorites(favorites)
    return favorites


def remove_favorite_folder(folder_path):
    """Remove a folder from the favorites list."""
    if not folder_path:
        return []

    normalized = os.path.abspath(folder_path)
    favorites = [folder for folder in load_favorites() if os.path.isdir(folder) and folder != normalized]
    save_favorites(favorites)
    return favorites


def update_favorites_selector(selector, favorites):
    """Refresh the favorites combobox values."""
    selector.config(values=favorites)
    if favorites:
        selector.set(favorites[0])
    else:
        selector.set("")


def format_report(result):
    """Create a readable text report for the GUI."""
    lines = []
    lines.append(f"Folder: {result['folder']}")
    lines.append(f"Files scanned: {len(result['files'])}")
    lines.append("")
    lines.append("Files by category:")
    for name, count in sorted(result['categories'].items()):
        if count:
            lines.append(f"- {name}: {count}")

    lines.append("")
    lines.append("Duplicate groups:")
    if result['duplicates']:
        for group in result['duplicates']:
            lines.append(f"- {len(group)} matching files")
            for path in group:
                lines.append(f"  {path}")
    else:
        lines.append("- None found")

    lines.append("")
    lines.append("Disk usage:")
    lines.append(f"- Total size: {result['stats']['total_size']} ({result['stats']['total_size_bytes']} bytes)")
    lines.append(f"- Total directories: {result['stats']['total_directories']}")
    lines.append(f"- Average file size: {result['stats']['average_file_size']}")
    lines.append("- Largest files:")
    for size, path in result['stats']['largest_files']:
        lines.append(f"  {statfinder.human_readable_size(size)}  {path}")

    return "\n".join(lines)


def create_app():
    """Create and launch the desktop interface."""

    # Create basic window geometry
    root = tk.Tk()
    root.title("SmartFile")
    root.geometry("1600x900")
    root.minsize(1400, 820)
    root.state("zoomed")
    main_frame = ttk.Frame(root, padding=8)
    main_frame.pack(fill="both", expand=True)

    # Introduce the program and how to use
    ttk.Label(main_frame, text="SmartFile Analyzer", font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(main_frame, text="Select a folder to scan files, detect duplicates, and view disk usage.").pack(anchor="w", pady=(0, 8))

    # Will contain the folder that is being analyzed
    selector_frame = ttk.Frame(main_frame)
    selector_frame.pack(fill="x", pady=(0, 6))
    folder_var = tk.StringVar()
    ttk.Entry(selector_frame, textvariable=folder_var, width=90).pack(side="left", fill="x", expand=True)
    
    # Browse button to get filepath
    ttk.Button(selector_frame, text="Browse", command=lambda: select_folder(folder_var)).pack(side="left", padx=(8, 0))

    # Favorites section
    favorites_var = tk.StringVar()
    favorite_selector = ttk.Combobox(selector_frame, textvariable=favorites_var, state="readonly", width=40)
    favorite_selector.pack(side="left", padx=(8, 0))

    def save_current_folder_as_favorite():
        """Saves the currently selected folder as a favorite"""
        current_folder = folder_var.get().strip()
        if not current_folder:
            messagebox.showwarning("No folder selected", "Choose a folder before saving it as a favorite.")
            return
        favorites = add_favorite_folder(current_folder)
        update_favorites_selector(favorite_selector, favorites)
        favorites_var.set(current_folder)

    def apply_selected_favorite():
        """Sets the chosen favorite folder as the selected folder"""
        selected_folder = favorites_var.get().strip()
        if selected_folder:
            folder_var.set(selected_folder)

    def remove_selected_favorite():
        """Removes a folder from the favorites list"""
        selected_folder = favorites_var.get().strip()
        if not selected_folder:
            return
        favorites = remove_favorite_folder(selected_folder)
        update_favorites_selector(favorite_selector, favorites)

    # Favorites buttons
    ttk.Button(selector_frame, text="Add Favorite", command=save_current_folder_as_favorite).pack(side="left", padx=(8, 0))
    ttk.Button(selector_frame, text="Use Favorite", command=apply_selected_favorite).pack(side="left", padx=(4, 0))
    ttk.Button(selector_frame, text="Remove", command=remove_selected_favorite).pack(side="left", padx=(4, 0))

    # Update favorites dropdown if favorites exist
    update_favorites_selector(favorite_selector, load_favorites())

    # Progress bar for analysis
    progress_frame = ttk.Frame(main_frame)
    progress_frame.pack(fill="x", pady=(0, 6))
    progress_var = tk.DoubleVar(value=0.0)
    status_var = tk.StringVar(value="Waiting to analyze a folder.")
    ttk.Progressbar(progress_frame, variable=progress_var, maximum=1.0, mode="determinate").pack(fill="x", expand=True)
    ttk.Label(progress_frame, textvariable=status_var).pack(anchor="w", pady=(4, 0))

    # Frame to contain more buttons
    button_row = ttk.Frame(main_frame)
    button_row.pack(fill="x", pady=(0, 6))

    # Button to start analysis
    analyze_button = ttk.Button(button_row, text="Analyze Folder")
    analyze_button.pack(side="left")

    # Export report as txt file
    export_button = ttk.Button(button_row, text="Export Report", state="disabled")
    export_button.pack(side="left", padx=(8, 0))

    # Delete duplicates found during analysis
    delete_button = ttk.Button(button_row, text="Delete Duplicates", state="disabled")
    delete_button.pack(side="left", padx=(8, 0))

    # Frame to hold filesorting stuff
    organize_frame = ttk.LabelFrame(main_frame, text="Organize Files", padding=8)
    organize_frame.pack(fill="x", pady=(0, 6))

    source_var = tk.StringVar()
    destination_var = tk.StringVar()
    move_var = tk.BooleanVar(value=False)

    # Source folder selector
    ttk.Label(organize_frame, text="Source folder:").grid(row=0, column=0, sticky="w")
    ttk.Entry(organize_frame, textvariable=source_var, width=80).grid(row=0, column=1, padx=(6, 6), pady=(0, 6), sticky="ew")
    ttk.Button(organize_frame, text="Browse", command=lambda: select_folder(source_var)).grid(row=0, column=2, pady=(0, 6))

    # Destination folder selector
    ttk.Label(organize_frame, text="Destination folder:").grid(row=1, column=0, sticky="w")
    ttk.Entry(organize_frame, textvariable=destination_var, width=80).grid(row=1, column=1, padx=(6, 6), pady=(0, 6), sticky="ew")
    ttk.Button(organize_frame, text="Browse", command=lambda: select_folder(destination_var)).grid(row=1, column=2, pady=(0, 6))

    # Checkbox to move files from source to destination (copies by default)
    ttk.Checkbutton(organize_frame, text="Move files instead of copying", variable=move_var).grid(row=2, column=1, sticky="w")
    organize_button = ttk.Button(organize_frame, text="Organize Files")
    organize_button.grid(row=2, column=2, sticky="e")

    # Frame for pie charts
    chart_frame = ttk.LabelFrame(main_frame, text="Charts", padding=8)
    chart_frame.pack(fill="x", pady=(0, 6))
    chart_container = ttk.Frame(chart_frame)
    chart_container.pack(fill="x")

    # File chart (shows distribution of file types)
    file_chart_canvas = tk.Canvas(chart_container, width=420, height=180, bg="white", scrollregion=(0, 0, 560, 220))
    file_chart_canvas.pack(side="left", padx=(0, 8))

    # Storage chart (Shows storage taken up by each file type)
    storage_chart_canvas = tk.Canvas(chart_container, width=420, height=180, bg="white", scrollregion=(0, 0, 560, 220))
    storage_chart_canvas.pack(side="left")

    # Frame for previewing certain files
    preview_frame = ttk.LabelFrame(main_frame, text="Preview Files", padding=8)
    preview_frame.pack(fill="x", pady=(0, 6))
    preview_label = ttk.Label(preview_frame, text="No preview selected")
    preview_label.pack(anchor="w")

    preview_search_var = tk.StringVar()
    preview_file_var = tk.StringVar()

    # Search bar for files
    ttk.Label(preview_frame, text="Search files:").pack(anchor="w", pady=(6, 2))
    preview_search_entry = ttk.Entry(preview_frame, textvariable=preview_search_var, width=80)
    preview_search_entry.pack(fill="x", pady=(0, 6))

    # Dropdown menu of all previewable files
    ttk.Label(preview_frame, text="Preview file:").pack(anchor="w", pady=(6, 2))
    preview_selector = ttk.Combobox(preview_frame, textvariable=preview_file_var, state="disabled", width=80)
    preview_selector.pack(fill="x", pady=(0, 8))
    preview_selector.bind("<<ComboboxSelected>>", lambda event: show_preview(result_data.get("report"), preview_canvas, preview_label, preview_file_var, preview_selector, preview_search_var.get()))
    preview_search_entry.bind("<KeyRelease>", lambda event: show_preview(result_data.get("report"), preview_canvas, preview_label, preview_file_var, preview_selector, preview_search_var.get()))

    # Output box for file preview
    preview_canvas = tk.Canvas(preview_frame, width=220, height=140, bg="white")
    preview_canvas.pack(anchor="w", pady=(8, 0))

    # Frame for analysis report
    output_frame = ttk.LabelFrame(main_frame, text="Report", padding=8)
    output_frame.pack(fill="both", expand=True)
    output_box = tk.Text(output_frame, wrap="word", width=140, height=10)
    output_box.pack(side="left", fill="both", expand=True)

    # Scrollbar for report
    scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=output_box.yview)
    scrollbar.pack(side="right", fill="y")
    output_box.configure(yscrollcommand=scrollbar.set)

    result_data = {"report": None}

    def run_analysis():
        """Begin analyzing the selected folder"""

        # Get the folder path
        folder_path = folder_var.get()
        if not folder_path:
            messagebox.showwarning("No folder selected", "Choose a folder before analyzing.")
            return

        # Disable other buttons so function isn't interrupted
        analyze_button.config(state="disabled")
        export_button.config(state="disabled")
        
        # Clear report box and begin progress bar
        output_box.delete("1.0", tk.END)
        output_box.insert("1.0", "Analysis in progress...\n")
        progress_var.set(0.0)
        status_var.set("Starting analysis...")

        def progress_callback(message, value):
            root.after(0, lambda: update_progress(message, value))

        def update_progress(message, value):
            status_var.set(message)
            progress_var.set(value)
            root.update_idletasks()

        def worker():
            """Attempts to analyze folder"""
            try:
                result = analyze_folder(folder_path, progress_callback)
                result_data["report"] = result
                root.after(0, lambda: show_result(result, output_box))
            except Exception as exc:
                root.after(0, lambda exc=exc: show_error(exc))
            finally:
                root.after(0, lambda: analyze_button.config(state="normal"))
                root.after(0, lambda: export_button.config(state="normal" if result_data.get("report") else "disabled"))
                root.after(0, lambda: delete_button.config(state="normal" if result_data.get("report") and result_data["report"].get("duplicates") else "disabled"))

        # Use multithreading to increase performance
        threading.Thread(target=worker, daemon=True).start()

    def show_result(result, box):
        box.delete("1.0", tk.END)
        box.insert("1.0", format_report(result))
        draw_pie_chart(file_chart_canvas, result["categories"])
        draw_storage_chart(storage_chart_canvas, result)
        show_preview(result, preview_canvas, preview_label, preview_file_var, preview_selector, preview_search_var.get())
        delete_button.config(state="normal" if result.get("duplicates") else "disabled")

    def show_error(exc):
        messagebox.showerror("Analysis failed", str(exc))

    def delete_duplicates():
        report = result_data.get("report")
        if not report:
            messagebox.showwarning("No report", "Run an analysis before deleting duplicates.")
            return

        if not report.get("duplicates"):
            messagebox.showinfo("No duplicates", "No duplicate files were found in the last analysis.")
            return

        if not messagebox.askyesno("Delete duplicates", "Delete all duplicate files except one copy from each group?"):
            return

        delete_button.config(state="disabled")
        output_box.delete("1.0", tk.END)
        output_box.insert("1.0", "Deleting duplicates...\n")

        try:
            deleted_count = 0
            for group in report.get("duplicates", []):
                if not group:
                    continue
                for duplicate_path in group[1:]:
                    if os.path.exists(duplicate_path):
                        os.remove(duplicate_path)
                        deleted_count += 1

            refreshed_report = analyze_folder(report["folder"])
            result_data["report"] = refreshed_report
            show_result(refreshed_report, output_box)
            messagebox.showinfo("Duplicates deleted", f"Removed {deleted_count} duplicate file(s).")
        except Exception as exc:
            messagebox.showerror("Delete failed", str(exc))
        finally:
            delete_button.config(state="normal" if result_data.get("report") and result_data["report"].get("duplicates") else "disabled")

    def organize_now():
        source_path = source_var.get()
        destination_path = destination_var.get()
        if not source_path or not destination_path:
            messagebox.showwarning("Missing folders", "Choose both a source and destination folder first.")
            return

        try:
            results = sorter.organize_files(source_path, destination_path, move_files=move_var.get())
            output_box.delete("1.0", tk.END)
            output_box.insert("1.0", f"Organized {len(results)} files.\n")
            for source_file, target_file in results:
                output_box.insert(tk.END, f"- {source_file} -> {target_file}\n")
            messagebox.showinfo("Organization complete", f"Processed {len(results)} files.")
        except Exception as exc:
            messagebox.showerror("Organization failed", str(exc))

    def export_report():
        report = result_data.get("report")
        if not report:
            messagebox.showwarning("No report", "Run an analysis before exporting.")
            return

        report_text = format_report(report)
        default_name = f"smartfile_report_{os.path.basename(report['folder']).replace(' ', '_') or 'export'}.txt"
        file_path = filedialog.asksaveasfilename(
            title="Save report",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("PDF files", "*.pdf")],
        )
        if not file_path:
            return

        if file_path.lower().endswith(".pdf"):
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
            except ImportError:
                messagebox.showwarning("PDF export unavailable", "Install reportlab to export PDF files.")
                return

            try:
                pdf_canvas = canvas.Canvas(file_path, pagesize=letter)
                y = 750
                for line in report_text.splitlines():
                    pdf_canvas.drawString(40, y, line)
                    y -= 12
                    if y < 40:
                        pdf_canvas.showPage()
                        y = 750
                pdf_canvas.save()
            except Exception as exc:
                messagebox.showerror("PDF export failed", str(exc))
        else:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(report_text)

        messagebox.showinfo("Export complete", f"Report saved to:\n{file_path}")

    analyze_button.config(command=run_analysis)
    export_button.config(command=export_report)
    delete_button.config(command=delete_duplicates)
    organize_button.config(command=organize_now)
    root.mainloop()


def select_folder(folder_var):
    """Gets the directory requested by the user"""
    folder = filedialog.askdirectory(title="Select a folder to analyze")
    if folder:
        folder_var.set(folder)


if __name__ == "__main__":
    create_app()