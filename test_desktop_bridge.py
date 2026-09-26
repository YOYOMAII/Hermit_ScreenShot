import unittest
from unittest.mock import MagicMock, patch

from desktop_bridge import DesktopBridge


class DesktopBridgeTests(unittest.TestCase):
    def test_rejects_non_app_paths(self) -> None:
        bridge = DesktopBridge(5000)
        result = bridge.save_download("https://evil.test/x.docx", "x.docx")
        self.assertFalse(result["ok"])

    @patch("urllib.request.urlopen")
    def test_writes_chosen_file(self, urlopen_mock) -> None:
        import tempfile
        import sys
        import types

        fake_webview = types.SimpleNamespace(
            windows=[MagicMock()],
            SAVE_DIALOG=30,
        )
        fake_webview.windows[0].create_file_dialog = MagicMock()
        with patch.dict(sys.modules, {"webview": fake_webview}):
            bridge = DesktopBridge(5000)
            urlopen_mock.return_value.__enter__.return_value.read.return_value = b"doc"
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                path = tmp.name
            fake_webview.windows[0].create_file_dialog.return_value = (path,)
            result = bridge.save_download("/api/smart/files/abc/document.docx", "report.docx")
        self.assertTrue(result["ok"])
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"doc")


if __name__ == "__main__":
    unittest.main()
