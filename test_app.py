"""Integration checks for the local upload page."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import app as web_app


class UploadPageTests(unittest.TestCase):
    def test_upload_returns_numbered_images_and_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(web_app, "OUTPUT_ROOT", Path(folder)):
                with web_app.app.test_client() as client:
                    response = client.post("/api/render", data={
                        "files": (io.BytesIO(b"<p>hello</p>\n" * 21), "index.html"),
                        "lines": "20", "name_style": "simple",
                    }, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual([item["name"] for item in response.json["images"]],
                                     ["index1.png", "index2.png"])
                    image_response = client.get(response.json["images"][0]["url"])
                    archive_response = client.get(response.json["zip_url"])
                    self.assertEqual(image_response.status_code, 200)
                    self.assertEqual(archive_response.status_code, 200)
                    image_response.close()
                    archive_response.close()

    def test_long_line_on_later_page_does_not_widen_earlier_images(self):
        source = ("<p>short</p>\n" * 25 + "<p>" + "x" * 900 + "</p>\n").encode()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(web_app, "OUTPUT_ROOT", Path(folder)):
                with web_app.app.test_client() as client:
                    response = client.post("/api/render", data={
                        "files": (io.BytesIO(source), "index.html"),
                        "lines": "25", "font_size": "30", "width": "1500",
                    }, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 200, response.json)
                    batch = Path(folder) / response.json["batch"]
                    with Image.open(batch / "index1.png") as first, \
                            Image.open(batch / "index2.png") as second:
                        self.assertEqual(first.width, 1500)
                        self.assertGreater(second.width, first.width)

    def test_rejects_other_file_types(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(web_app, "OUTPUT_ROOT", Path(folder)):
                with web_app.app.test_client() as client:
                    response = client.post("/api/render", data={
                        "files": (io.BytesIO(b"hello"), "notes.txt"),
                    }, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(list(Path(folder).iterdir()), [])

    def test_non_english_and_special_file_names(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(web_app, "OUTPUT_ROOT", Path(folder)):
                with web_app.app.test_client() as client:
                    for filename, expected in (("索引.html", "索引1.png"),
                                               ("ပုံစံ.css", "ပုံစံ1.png"),
                                               ("page#2 draft.html", "page_2 draft1.png"),
                                               ("../../con.html", "_con1.png")):
                        response = client.post("/api/render", data={
                            "files": (io.BytesIO(b"<p>hi</p>\n"), filename),
                        }, content_type="multipart/form-data")
                        self.assertEqual(response.status_code, 200, response.json)
                        image = response.json["images"][0]
                        self.assertEqual(image["name"], expected)
                        fetched = client.get(image["url"])
                        self.assertEqual(fetched.status_code, 200)
                        fetched.close()

    def test_unexpected_errors_return_json_and_clean_up(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(web_app, "OUTPUT_ROOT", Path(folder)), \
                    patch.object(web_app, "main", side_effect=RuntimeError("boom")):
                with web_app.app.test_client() as client:
                    response = client.post("/api/render", data={
                        "files": (io.BytesIO(b"<p>hi</p>\n"), "index.html"),
                    }, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 500)
                    self.assertIn("Something went wrong", response.json["error"])
                    self.assertEqual(list(Path(folder).iterdir()), [])

    def test_old_results_are_deleted_but_other_files_are_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            shots, smart = Path(folder) / "code_screenshots", Path(folder) / "smart_documents"
            old_batch, new_batch, old_doc = shots / "0123456789ab", shots / "ba9876543210", smart / "aaaaaaaaaaaa"
            cli_image, cli_folder = shots / "index1.png", shots / "example"
            for path in (old_batch, new_batch, old_doc, cli_folder):
                path.mkdir(parents=True)
                (path / "file.png").write_bytes(b"png")
            cli_image.write_bytes(b"png")
            two_hours_ago = time.time() - 2 * 3600
            for path in (old_batch, old_doc, cli_image, cli_folder):
                os.utime(path, (two_hours_ago, two_hours_ago))
            with patch.object(web_app, "OUTPUT_ROOT", shots), patch.object(web_app, "SMART_ROOT", smart):
                web_app.remove_old_results()
            self.assertFalse(old_batch.exists())
            self.assertFalse(old_doc.exists())
            self.assertTrue(new_batch.exists())
            self.assertTrue(cli_image.exists())
            self.assertTrue(cli_folder.exists())

    def test_gallery_keeps_page_numbers_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(web_app, "OUTPUT_ROOT", Path(folder)):
                with web_app.app.test_client() as client:
                    response = client.post("/api/render", data={
                        "files": (io.BytesIO(b"<p>line</p>\n" * 11), "index.html"),
                        "lines": "1",
                    }, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual([item["name"] for item in response.json["images"]],
                                     [f"index{number}.png" for number in range(1, 12)])


if __name__ == "__main__":
    unittest.main()
