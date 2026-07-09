import os
import shutil
import tempfile
import unittest
from pathlib import Path

import duplicatefinder
import scanner
import sorter
import statfinder


class SmartFileCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.file_a = self.root / "alpha.txt"
        self.file_a.write_text("same content\n", encoding="utf-8")

        self.file_b = self.root / "beta.txt"
        self.file_b.write_text("same content\n", encoding="utf-8")

        self.file_c = self.root / "gamma.bin"
        self.file_c.write_bytes(b"different-bytes")

        subfolder = self.root / "nested"
        subfolder.mkdir()
        self.file_d = subfolder / "delta.txt"
        self.file_d.write_text("nested file\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_folder_returns_files_recursively(self):
        files = scanner.scan_folder(str(self.root))
        self.assertEqual(len(files), 4)
        self.assertTrue(any(path.name == "alpha.txt" for path in files))
        self.assertTrue(any(path.name == "delta.txt" for path in files))

    def test_find_duplicate_files_groups_identical_content(self):
        file_lookup = {
            "text": [self.file_a, self.file_b, self.file_c],
        }
        duplicates = duplicatefinder.find_duplicate_files(file_lookup)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(len(duplicates[0]), 2)
        self.assertIn(self.file_a, duplicates[0])
        self.assertIn(self.file_b, duplicates[0])

    def test_sort_files_assigns_expected_categories(self):
        file_list = [self.file_a, self.file_c, self.file_d]
        grouped = sorter.sort_files(file_list)
        self.assertIn(self.file_a, grouped["text"])
        self.assertIn(self.file_c, grouped["other"])
        self.assertIn(self.file_d, grouped["text"])

    def test_get_folder_stats_reports_totals(self):
        stats = statfinder.get_folder_stats(str(self.root))
        self.assertGreater(stats["total_size_bytes"], 0)
        self.assertEqual(stats["total_files"], 4)
        self.assertGreaterEqual(stats["total_directories"], 1)
        self.assertIn("B", stats["total_size"])

    def test_human_readable_size_formats_bytes(self):
        self.assertEqual(statfinder.human_readable_size(10), "10.00B")
        self.assertEqual(statfinder.human_readable_size(1536), "1.50KB")


if __name__ == "__main__":
    unittest.main()
