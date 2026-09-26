"""Focused checks for splitting, source fidelity, and rendered output."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pygments.token import Comment, Name

from code_screenshot import Guide, main, prepare_file, source_lines, structural_guides


class CodeScreenshotTests(unittest.TestCase):
    def test_line_split_preserves_blank_lines_and_crlf(self):
        self.assertEqual(source_lines("one\r\n\r\ntwo\r\n"), ["one", "", "two"])
        self.assertEqual(source_lines(""), [""])

    def test_highlighting_retains_every_character(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            original = '<div class="x">\n\t<!-- note -->\n</div>\n'
            path.write_text(original, encoding="utf-8")
            language, lines = prepare_file(path)
            self.assertEqual(language, "HTML")
            self.assertEqual(["".join(part for _, part in line) for line in lines],
                             source_lines(original))
            self.assertTrue(any(token in Name.Tag for token, _ in lines[0]))
            self.assertTrue(any(token in Comment for token, _ in lines[1]))

    def test_fit_width_keeps_long_lines_from_widening_other_images(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text("<p>short</p>\n<p>" + "long " * 400 + "</p>\n", encoding="utf-8")
            for flag, name in (([], "shared"), (["--fit-width"], "fit")):
                main([str(path), "--output", str(Path(folder) / name), "--lines", "1"] + flag)
            shared = [Image.open(Path(folder) / "shared" / f"index{n}.png").width for n in (1, 2)]
            fit = [Image.open(Path(folder) / "fit" / f"index{n}.png").width for n in (1, 2)]
            self.assertEqual(shared[0], shared[1])
            self.assertEqual(fit, [1200, shared[1]])

    def test_html_guides_follow_matching_aligned_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text("<main>\n  <section>\n    <p>Hi</p>\n"
                            "  </section>\n</main>\n", encoding="utf-8")
            language, lines = prepare_file(path)
            self.assertEqual(structural_guides(language, lines, 4),
                             [Guide(2, 4, 0), Guide(3, 3, 2)])

    def test_html_guides_skip_misaligned_and_fake_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text("<!-- <main> -->\n<main>\n  <p>Hi</p>\n"
                            " </main>\n<meta\n  name=\"x\"\n  content=\"y\"\n/>\n",
                            encoding="utf-8")
            language, lines = prepare_file(path)
            self.assertEqual(structural_guides(language, lines, 4),
                             [Guide(6, 7, 0)])

    def test_css_guides_use_braces_outside_strings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "style.css"
            path.write_text('.card {\n  content: "}";\n  color: red;\n}\n'
                            '.bad {\n  color: blue;\n  }\n', encoding="utf-8")
            language, lines = prepare_file(path)
            self.assertEqual(structural_guides(language, lines, 4),
                             [Guide(2, 3, 0)])

    def test_pages_names_shared_width_and_last_page_height(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "index.html"
            source.write_text("\n".join(["<p>line</p>"] * 20 +
                                        ["<p>" + "x" * 140 + "</p>"]) + "\n",
                              encoding="utf-8")
            output = root / "shots"
            self.assertEqual(main([str(source), "--output", str(output)]), 0)
            images = sorted(output.glob("*.png"))
            self.assertEqual([image.name for image in images], ["index1.png", "index2.png"])
            with Image.open(images[0]) as first, Image.open(images[1]) as second:
                self.assertEqual(first.width, second.width)
                self.assertGreater(first.width, 1200)
                self.assertGreater(first.height, second.height)
                self.assertEqual(first.format, "PNG")
                self.assertEqual(first.getpixel((0, 0)), (239, 240, 241))

    def test_matched_guide_continues_across_page_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "index.html"
            source.write_text("<main>\n" + "  <p>Line</p>\n" * 23 + "</main>\n",
                              encoding="utf-8")
            output = root / "shots"
            main([str(source), "--output", str(output)])
            # Source line 21 starts the second image while <main> is still open.
            with Image.open(output / "index2.png") as second:
                self.assertEqual(second.getpixel((102, 17)), (210, 217, 218))

    def test_unusual_markup_renders_without_guides(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text("<![if !IE]>\n<p>x</p>\n<![foo]>\n<![\n", encoding="utf-8")
            language, lines = prepare_file(path)
            self.assertEqual(structural_guides(language, lines, 4), [])
            self.assertEqual(main([str(path), "--output", str(Path(folder) / "shots")]), 0)

    def test_minified_line_is_refused_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bootstrap.min.css"
            path.write_text(".a{color:red}" * 20000, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bootstrap.min.css line 1 is too long"):
                main([str(path), "--output", str(Path(folder) / "shots")])

    def test_non_utf8_message_names_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.css"
            path.write_bytes("a{content:'é'}".encode("latin-1"))
            with self.assertRaisesRegex(ValueError, "^old.css is not saved as UTF-8"):
                prepare_file(path)

    def test_padded_naming_and_css(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "style.css"
            source.write_text("/* comment */\nbody { color: blue; }\n", encoding="utf-8")
            output = root / "shots"
            self.assertEqual(main([str(source), "--output", str(output),
                                   "--name-style", "padded", "--lines", "1"]), 0)
            self.assertEqual(sorted(p.name for p in output.glob("*.png")),
                             ["style_001.png", "style_002.png"])

    def test_page_names_never_overwrite_another_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.html").write_text("<p>x</p>\n" * 11, encoding="utf-8")
            (root / "a1.html").write_text("<p>y</p>\n", encoding="utf-8")
            (root / "b.html").write_text("<p>x</p>\n", encoding="utf-8")
            (root / "B.css").write_text("p {}\n", encoding="utf-8")
            output = root / "shots"
            main([str(root / name) for name in ("a.html", "a1.html", "b.html", "B.css")]
                 + ["--output", str(output), "--lines", "1"])
            names = [p.name for p in output.glob("*.png")]
            self.assertEqual(len(names), 11 + 1 + 1 + 1)
            self.assertIn("a11.png", names)
            self.assertIn("a1_21.png", names)
            self.assertEqual({"b_html1.png", "B_css1.png"} - set(names), set())

    def test_too_many_images_are_refused_before_rendering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text("<p>x</p>\n" * 501, encoding="utf-8")
            output = Path(folder) / "shots"
            with self.assertRaisesRegex(ValueError, "more than 500 images"):
                main([str(path), "--output", str(output), "--lines", "1"])
            with self.assertRaisesRegex(ValueError, "more than 500 images"):
                main([str(path), "--output", str(output), "--lines", "100"], max_images=5)
            self.assertFalse(output.exists())

    def test_oversized_image_is_refused_before_rendering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wide.css"
            path.write_text(("x" * 900 + "\n") * 100, encoding="utf-8")
            output = Path(folder) / "shots"
            with self.assertRaisesRegex(ValueError, "wide.css lines 1-100 would make a"):
                main([str(path), "--output", str(output), "--lines", "100",
                      "--font-size", "48"])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
