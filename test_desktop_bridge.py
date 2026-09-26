import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from desktop_bridge import DesktopBridge, safe_file_name


def fake_response(data: bytes):
    response = patch("urllib.request.urlopen").start()
    response.return_value.__enter__.return_value.read.return_value = data
    return response


class DesktopBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.bridge = DesktopBridge(5000, folder=self.folder)

    def tearDown(self) -> None:
        patch.stopall()

    def test_rejects_non_app_paths(self) -> None:
        for bad in ("https://evil.test/x.docx", "//evil.test/x.docx", "", None):
            self.assertFalse(self.bridge.save_download(bad, "x.docx")["ok"])

    def test_saves_new_file_in_downloads_without_overwriting(self) -> None:
        fake_response(b"doc")
        first = self.bridge.save_download("/api/smart/files/abc/document.docx", "report.docx")
        second = self.bridge.save_download("/api/smart/files/abc/document.docx", "report.docx")
        self.assertTrue(first["ok"] and second["ok"])
        self.assertEqual(first["name"], "report.docx")
        self.assertEqual(second["name"], "report (1).docx")
        self.assertEqual(Path(second["path"]).read_bytes(), b"doc")
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["report (1).docx", "report.docx"])

    def test_strips_folders_and_bad_characters_from_name(self) -> None:
        self.assertEqual(safe_file_name("../../etc/pa:ss?.docx"), "pa_ss_.docx")
        self.assertEqual(safe_file_name(""), "download")
        fake_response(b"x")
        result = self.bridge.save_download("/api/x", "../outside.docx")
        self.assertEqual(Path(result["path"]).parent, self.folder)

    def test_expired_file_reports_clear_error(self) -> None:
        urlopen = patch("urllib.request.urlopen").start()
        urlopen.side_effect = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        result = self.bridge.save_download("/api/smart/files/old/document.docx", "a.docx")
        self.assertFalse(result["ok"])
        self.assertIn("expired", result["error"])
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_open_only_allows_files_it_saved(self) -> None:
        other = self.folder / "other.docx"
        other.write_bytes(b"x")
        self.assertFalse(self.bridge.open_file(str(other))["ok"])
        self.assertFalse(self.bridge.show_in_folder("/etc/passwd")["ok"])


if __name__ == "__main__":
    unittest.main()
