#!/usr/bin/env python3
"""Render HTML and CSS source files as VS Code inspired PNG screenshots."""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
    from pygments import lex
    from pygments.lexers import CssLexer, HtmlLexer
    from pygments.token import Comment, Keyword, Literal, Name, Number, Operator, Punctuation, String, Token
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install with: python -m pip install -r requirements.txt"
    ) from exc


Run = Tuple[object, str]
Line = List[Run]
NEWLINE = re.compile(r"\r\n|\r|\n")
SUPPORTED = {".html": ("HTML", HtmlLexer), ".css": ("CSS", CssLexer)}
VOID_HTML_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
# Wider images can't be shown by browsers or placed readably in a document,
# and a minified file's single line would otherwise need millions of pixels.
MAX_LINE_WIDTH = 32000
# With wrapping, a line needing more rows than this is minified code, not something to read.
MAX_WRAPPED_ROWS = 400
QUOTES = ("'", '"')
# Pillow refuses to open larger images as a possible decompression bomb.
MAX_IMAGE_PIXELS = 178_956_970
MAX_IMAGES = 500


@dataclass(frozen=True, order=True)
class Guide:
    first_line: int
    last_line: int
    column: int


@dataclass(frozen=True)
class Theme:
    chrome: str
    editor: str
    border: str
    foreground: str
    muted: str
    line_number: str
    tag: str
    attribute: str
    string: str
    comment: str
    css_property: str
    css_selector: str
    keyword: str
    number: str
    indent_guide: str
    active_background: str
    active_border: str
    caret: str


THEMES: Dict[str, Theme] = {
    "light": Theme(
        chrome="#F3F3F3", editor="#EFF0F1", border="#D8D8D8",
        foreground="#17191B", muted="#8D969A", line_number="#AAB2B4",
        tag="#258CCB", attribute="#B68600", string="#29A74D",
        comment="#849699", css_property="#247DB0", css_selector="#886700",
        keyword="#258CCB", number="#159456", indent_guide="#D2D9DA",
        active_background="#E4ECEC", active_border="#C5DADA", caret="#B68600",
    ),
    "light-modern": Theme(
        chrome="#F8F8F8", editor="#FFFFFF", border="#E5E5E5",
        foreground="#1F2328", muted="#687076", line_number="#8A8A8A",
        tag="#0550AE", attribute="#A34C00", string="#0A53A1",
        comment="#328143", css_property="#0756A7", css_selector="#8C3A35",
        keyword="#8250DF", number="#116329", indent_guide="#E1E5E7",
        active_background="#F1F5F8", active_border="#DCE6EA", caret="#4273DC",
    ),
    "dark": Theme(
        chrome="#252526", editor="#1E1E1E", border="#3C3C3C",
        foreground="#D4D4D4", muted="#A8A8A8", line_number="#858585",
        tag="#569CD6", attribute="#9CDCFE", string="#CE9178",
        comment="#6A9955", css_property="#9CDCFE", css_selector="#D7BA7D",
        keyword="#C586C0", number="#B5CEA8", indent_guide="#3B3B3B",
        active_background="#282D33", active_border="#37404A", caret="#D4D4D4",
    ),
}


def read_source(path: Path) -> str:
    """Decode without changing the file; a UTF-8 BOM is hidden as editors do."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} is not saved as UTF-8. Save it with UTF-8 "
                         "encoding in your editor and try again.") from exc


def source_lines(source: str) -> List[str]:
    """Count editor lines without making a new page for a final newline."""
    if not source:
        return [""]
    lines = NEWLINE.split(source)
    if source.endswith(("\r", "\n")):
        lines.pop()
    return lines


def highlighted_lines(source: str, lexer_type: type, expected: Sequence[str]) -> List[Line]:
    # Lexer settings avoid the default added final newline. Lex the whole file so
    # multiline comments, strings, and embedded language states stay intact.
    lexer = lexer_type(ensurenl=False, stripnl=False, stripall=False)
    lines: List[Line] = [[]]
    for token, value in lex(source, lexer):
        parts = NEWLINE.split(value)
        for index, part in enumerate(parts):
            if index:
                lines.append([])
            if part:
                lines[-1].append((token, part))
    if len(lines) > len(expected) and not lines[-1]:
        lines.pop()
    # Source text is authoritative if a lexer normalizes unusual input. Plain
    # text still preserves the characters rather than silently dropping them.
    if len(lines) != len(expected) or ["".join(text for _, text in line) for line in lines] != list(expected):
        return [[(Token.Text, text)] for text in expected]
    if lexer_type is HtmlLexer:
        for index, line in enumerate(lines):
            expanded = []
            for token, text in line:
                if token in Comment.Preproc and text.lower().startswith("<!doctype "):
                    match = re.fullmatch(r"(<!doctype\s+)([^>]*)(>)", text, flags=re.IGNORECASE)
                    if match:
                        expanded.extend(((Name.Tag, match.group(1)),
                                         (Name.Attribute, match.group(2)),
                                         (Punctuation, match.group(3))))
                        continue
                expanded.append((token, text))
            lines[index] = expanded
    return lines


def color_for(token: Token, text: str, language: str, theme: Theme) -> str:
    if token in Comment:
        return theme.comment
    if token in String or token in Literal.String:
        return theme.string
    if token in Number or token in Literal.Number:
        return theme.number
    if language == "HTML":
        if token in Punctuation and text in ("<", ">", "/"):
            return theme.tag
        if token in Name.Tag:
            return theme.tag
        if token in Name.Attribute:
            return theme.attribute
    else:
        if token in Name.Attribute or token in Name.Property:
            return theme.css_property
        if token in Name.Tag or token in Name.Class or token in Name.Function or token in Name.Namespace or token in Name.Pseudo:
            return theme.css_selector
    if token in Keyword:
        return theme.keyword
    if token in Operator or token in Punctuation:
        return theme.muted
    return theme.foreground


def load_font(size: int, requested: str | None = None) -> ImageFont.FreeTypeFont:
    choices = [requested] if requested else [
        "/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consola.ttf",
        "FiraCode-Regular.ttf", "DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Monaco.ttf",
    ]
    for choice in choices:
        if not choice:
            continue
        try:
            return ImageFont.truetype(choice, size)
        except OSError:
            pass
    if requested:
        raise ValueError(f"Cannot open font: {requested}")
    raise ValueError("No monospaced font found. Supply a font file with --font.")


def comment_font(font: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
    """Use real italic glyphs where the selected font provides them."""
    if Path(getattr(font, "path", "")).name.lower() == "menlo.ttc":
        try:
            return font.font_variant(index=2)
        except OSError:
            pass
    return font


def whitespace_columns(text: str, tab_width: int) -> int:
    columns = 0
    for character in text:
        if character == " ":
            columns += 1
        elif character == "\t":
            columns += tab_width - columns % tab_width
        else:
            break
    return columns


class GuideParseError(Exception):
    pass


class HtmlGuideParser(HTMLParser):
    """Find only correctly matched and visually aligned HTML scopes."""

    def error(self, message: str) -> None:
        # Python 3.9's markup base calls this for input such as "<![foo]>".
        raise GuideParseError(message)

    def __init__(self, source_lines: Sequence[str], tab_width: int) -> None:
        super().__init__(convert_charrefs=False)
        self.source_lines = source_lines
        self.tab_width = tab_width
        self.stack: List[Tuple[str, int, int | None]] = []
        self.guides: List[Guide] = []

    def aligned_column(self) -> int | None:
        line, offset = self.getpos()
        if line < 1 or line > len(self.source_lines):
            return None
        prefix = self.source_lines[line - 1][:offset]
        if any(character not in " \t" for character in prefix):
            return None
        return whitespace_columns(prefix, self.tab_width)

    def start_tag(self, tag: str, self_closing: bool) -> None:
        start_line, _ = self.getpos()
        raw = self.get_starttag_text() or ""
        end_line = start_line + len(NEWLINE.findall(raw))
        column = self.aligned_column()
        # A tag with attributes on later lines has its own continuation guide.
        if column is not None and end_line > start_line + 1:
            self.guides.append(Guide(start_line + 1, end_line - 1, column))
        if not self_closing and tag not in VOID_HTML_TAGS:
            self.stack.append((tag, end_line, column))

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.start_tag(tag, False)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.start_tag(tag, True)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1][0] != tag:
            return
        _, start_end_line, opening_column = self.stack.pop()
        closing_line, _ = self.getpos()
        closing_column = self.aligned_column()
        if (opening_column is not None and opening_column == closing_column
                and closing_line > start_end_line + 1):
            self.guides.append(Guide(start_end_line + 1, closing_line - 1,
                                     opening_column))


def structural_guides(language: str, lines: Sequence[Line], tab_width: int) -> List[Guide]:
    plain_lines = ["".join(text for _, text in line) for line in lines]
    if language == "HTML":
        parser = HtmlGuideParser(plain_lines, tab_width)
        try:
            parser.feed("\n".join(plain_lines))
            parser.close()
        except (GuideParseError, AssertionError, NotImplementedError):
            # Guides are decoration; unusual markup still renders without them.
            return []
        return sorted(set(parser.guides))

    # CSS braces are classified by Pygments, so braces in comments or strings
    # never open a guide. A closing brace must align with its selector line.
    guides: List[Guide] = []
    stack: List[Tuple[int, int]] = []
    for line_number, line in enumerate(lines, start=1):
        plain = plain_lines[line_number - 1]
        opening_column = whitespace_columns(plain, tab_width)
        offset = 0
        for token, value in line:
            if token in Punctuation:
                for character_index, character in enumerate(value):
                    if character == "{":
                        stack.append((line_number, opening_column))
                    elif character == "}" and stack:
                        opening_line, column = stack.pop()
                        prefix = plain[:offset + character_index]
                        if (all(character in " \t" for character in prefix) and
                                whitespace_columns(prefix, tab_width) == column and
                                line_number > opening_line + 1):
                            guides.append(Guide(opening_line + 1,
                                                line_number - 1, column))
            offset += len(value)
    return sorted(set(guides))


def segment_width(text: str, x: float, origin: float, font: ImageFont.FreeTypeFont, tab_width: int) -> float:
    """Measure a run, expanding tabs to VS Code style tab stops."""
    tab_pixels = font.getlength(" ") * tab_width
    for section in re.split(r"(\t)", text):
        if section == "\t":
            x = origin + (int((x - origin) / tab_pixels) + 1) * tab_pixels
        elif section:
            x += font.getlength(section)
    return x


def draw_run(
    draw: ImageDraw.ImageDraw, text: str, x: float, y: int, origin: float,
    font: ImageFont.FreeTypeFont, tab_width: int, color: str,
) -> float:
    for section in re.split(r"(\t)", text):
        if section == "\t":
            x = segment_width(section, x, origin, font, tab_width)
        elif section:
            draw.text((round(x), y), section, font=font, fill=color, anchor="la")
            x += font.getlength(section)
    return x


def wrap_line(
    runs: Line, text_x: float, limit: float, font: ImageFont.FreeTypeFont, tab_width: int,
) -> List[Tuple[float, Line]]:
    """Split one line into (start x, runs) rows that end before limit, like VS Code word wrap.

    Rows break after whitespace where possible. Continuation rows keep the
    line's indentation unless that would leave too little room for code.
    """
    chars = [(token, character) for token, text in runs for character in text]
    plain = "".join(character for _, character in chars)
    leading = plain[:len(plain) - len(plain.lstrip(" \t"))]
    indent = segment_width(leading, text_x, text_x, font, tab_width) - text_x
    if indent > (limit - text_x) / 2:
        indent = 0.0
    tab_pixels = font.getlength(" ") * tab_width
    widths: Dict[str, float] = {}

    def row(part: Sequence[Tuple[object, str]]) -> Line:
        return [(token, "".join(character for _, character in group))
                for token, group in groupby(part, key=itemgetter(0))]

    rows: List[Tuple[float, Line]] = []
    start, row_x = 0, float(text_x)
    while True:
        x, index, break_at, has_code = row_x, start, None, False
        while index < len(chars):
            character = chars[index][1]
            if character == "\t":
                end = text_x + (int((x - text_x) / tab_pixels) + 1) * tab_pixels
            else:
                if character not in widths:
                    widths[character] = font.getlength(character)
                end = x + widths[character]
            if end > limit and index > start:
                break
            x = end
            index += 1
            if character not in " \t":
                has_code = True
            elif has_code:
                break_at = index
        if index == len(chars):
            rows.append((row_x, row(chars[start:])))
            return rows
        cut = break_at or index
        rows.append((row_x, row(chars[start:cut])))
        start, row_x = cut, text_x + indent


def prepare_file(path: Path) -> Tuple[str, List[Line]]:
    if not path.is_file():
        raise ValueError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {path} (use .html or .css)")
    language, lexer_type = SUPPORTED[suffix]
    source = read_source(path)
    expected = source_lines(source)
    return language, highlighted_lines(source, lexer_type, expected)


def page_layout(font_size: int, show_header: bool) -> Tuple[int, int, int, int]:
    """Return line height, title height, top padding, and bottom padding."""
    line_height = round(font_size * 1.52)
    title_height = max(54, round(font_size * 2.15)) if show_header else 0
    top_pad = round(font_size * 0.8) if show_header else round(font_size * 0.45)
    bottom_pad = round(font_size * 0.9) if show_header else round(font_size * 0.55)
    return line_height, title_height, top_pad, bottom_pad


def render_page(
    path: Path, language: str, lines: Sequence[Line], first_line: int, full_width: int,
    line_digits: int, font: ImageFont.FreeTypeFont, theme: Theme, tab_width: int,
    output_path: Path, font_size: int, guides: Sequence[Guide],
    active_line: int, show_header: bool,
    rows: Sequence[Sequence[Tuple[float, Line]]] | None = None,
) -> None:
    """Draw one page; rows holds each line's wrapped (start x, runs) rows when wrapping."""
    line_height, title_height, top_pad, bottom_pad = page_layout(font_size, show_header)
    left_pad = 28
    gutter_width = max(50, round(font.getlength("0" * line_digits)) + 10)
    text_x = left_pad + gutter_width + 24
    if rows is None:
        rows = [[(float(text_x), runs)] for runs in lines]
    tops = []
    row_count = 0
    for line_rows in rows:
        tops.append(row_count)
        row_count += len(line_rows)
    height = title_height + top_pad + line_height * row_count + bottom_pad
    image = Image.new("RGB", (full_width, height), theme.editor)
    draw = ImageDraw.Draw(image)

    if show_header:
        draw.rectangle((0, 0, full_width - 1, title_height - 1), fill=theme.chrome)
        draw.line((0, title_height - 1, full_width, title_height - 1), fill=theme.border, width=1)
        marker = "#E34C26" if language == "HTML" else "#264DE4"
        draw.rounded_rectangle((22, 18, 36, 32), radius=3, fill=marker)
        title_font = load_font(max(14, round(font_size * 0.68)))
        title = f"{path.name}  |  {language}  |  Lines {first_line}-{first_line + len(lines) - 1}"
        draw.text((47, 13), title, font=title_font, fill=theme.foreground, anchor="la")

    italic_font = comment_font(font)
    code_top = title_height + top_pad
    last_line = first_line + len(lines) - 1
    if first_line <= active_line <= last_line:
        active_index = active_line - first_line
        active_y = code_top + tops[active_index] * line_height
        active_bottom = active_y + len(rows[active_index]) * line_height - 1
        draw.rectangle((text_x - 4, active_y, full_width - 1, active_bottom),
                       fill=theme.active_background)
        draw.line((text_x - 4, active_y, full_width - 1, active_y),
                  fill=theme.active_border)
        draw.line((text_x - 4, active_bottom, full_width - 1, active_bottom),
                  fill=theme.active_border)

    # Use the opening tag/selector's actual visual column. A guide crosses a
    # page boundary only while its matching block remains open.
    for guide in guides:
        visible_start = max(guide.first_line, first_line)
        visible_end = min(guide.last_line, last_line)
        if visible_start > visible_end:
            continue
        guide_x = round(text_x + font.getlength(" ") * guide.column)
        start_index, end_index = visible_start - first_line, visible_end - first_line
        start_y = code_top + tops[start_index] * line_height
        end_y = code_top + (tops[end_index] + len(rows[end_index])) * line_height - 1
        draw.line((guide_x, start_y, guide_x, end_y),
                  fill=theme.indent_guide, width=1)

    for index, line_rows in enumerate(rows):
        y = code_top + tops[index] * line_height
        is_active = first_line + index == active_line
        number = str(first_line + index)
        number_width = font.getlength(number)
        draw.text((round(left_pad + gutter_width - number_width), y), number,
                  font=font, fill=theme.foreground if is_active else theme.line_number,
                  anchor="la")
        last_attribute = ""
        # A wrapped link continues on the next row, so its quotes may be on different rows.
        link_open = False
        for row_index, (x, runs) in enumerate(line_rows):
            y = code_top + (tops[index] + row_index) * line_height
            for token, text in runs:
                start_x = x
                chosen_font = italic_font if token in Comment else font
                color = color_for(token, text, language, theme)
                x = draw_run(draw, text, x, y, text_x, chosen_font, tab_width, color)
                if language == "HTML":
                    if token in Name.Attribute:
                        last_attribute = text.lower()
                    elif token in String and last_attribute in ("href", "src"):
                        opening = not link_open and text.startswith(QUOTES)
                        closing = text.endswith(QUOTES) and (link_open or len(text) > 1)
                        quote_width = font.getlength(text[0]) if opening else 0
                        right_quote_width = font.getlength(text[-1]) if closing else 0
                        draw.line((round(start_x + quote_width), y + font_size + 3,
                                   round(x - right_quote_width), y + font_size + 3),
                                  fill=color, width=1)
                        link_open = (opening or link_open) and not closing
                        if not link_open:
                            last_attribute = ""
                    elif token in Name.Tag or token in Punctuation and text in ("<", ">"):
                        last_attribute = ""
        if is_active:
            draw.line((round(x), y + 2, round(x), y + font_size + 9),
                      fill=theme.caret, width=2)

    image.save(output_path, "PNG", optimize=True, dpi=(144, 144))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn HTML/CSS files into VS Code style code screenshots."
    )
    parser.add_argument("files", nargs="+", type=Path, help="One or more .html or .css files")
    parser.add_argument("--lines-per-image", "--lines", type=int, default=20, metavar="N",
                        help="Lines in each PNG (default: 20)")
    parser.add_argument("--font-size", type=int, default=24, metavar="PX",
                        help="Code font size in pixels (default: 24)")
    parser.add_argument("--font", metavar="PATH", help="Path to a monospaced .ttf/.otf/.ttc font")
    parser.add_argument("--output", type=Path, default=Path("code_screenshots"), metavar="DIR",
                        help="Output folder (default: ./code_screenshots)")
    parser.add_argument("--theme", choices=sorted(THEMES), default="light",
                        help="Color theme (default: light)")
    parser.add_argument("--width", type=int, default=1200, metavar="PX",
                        help="Minimum width; expands for long lines unless --wrap (default: 1200)")
    parser.add_argument("--tab-width", type=int, default=4, metavar="N",
                        help="Visual spaces per tab (default: 4)")
    parser.add_argument("--name-style", choices=("simple", "padded"), default="simple",
                        help="simple: index1.png; padded: index_001.png")
    parser.add_argument("--active-line", type=int, default=0, metavar="N",
                        help="Highlight one source line like an editor cursor (0 disables it)")
    parser.add_argument("--header", action="store_true",
                        help="Include the optional file/language/line-range bar")
    parser.add_argument("--fit-width", action="store_true",
                        help="Size each PNG to its own longest line instead of sharing one width")
    parser.add_argument("--wrap", action="store_true",
                        help="Wrap lines wider than --width onto extra rows, like VS Code word wrap")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, max_images: int = MAX_IMAGES) -> int:
    """Render the files; max_images lets a caller spread one batch limit over several calls."""
    args = parse_args(argv)
    if (args.lines_per_image < 1 or args.font_size < 8 or args.width < 200
            or args.tab_width < 1 or args.active_line < 0):
        raise ValueError("Use positive lines/tab width, font size >= 8, width >= 200, and active line >= 0.")
    files = list(dict.fromkeys(path.expanduser().resolve() for path in args.files))
    prepared = [(path, *prepare_file(path)) for path in files]

    def page_count_for(lines: Sequence[Line]) -> int:
        return (len(lines) + args.lines_per_image - 1) // args.lines_per_image

    if sum(page_count_for(lines) for _, _, lines in prepared) > max_images:
        raise ValueError(f"These files would make more than {MAX_IMAGES} images in one batch. "
                         "Use more lines per image or upload fewer files at a time.")
    font = load_font(args.font_size, args.font)
    max_line_number = max(len(lines) for _, _, lines in prepared)
    line_digits = len(str(max_line_number))
    gutter_width = max(50, round(font.getlength("0" * line_digits)) + 10)
    text_x = 28 + gutter_width + 24
    title_font = load_font(max(14, round(args.font_size * 0.68))) if args.header else None

    def too_long(path: Path, line_number: int) -> ValueError:
        return ValueError(
            f"{path.name} line {line_number} is too long for a screenshot. "
            "Minified files can't be shown readably; use the original, "
            "formatted file or split the line.")

    def needed_width(path: Path, language: str, lines: Sequence[Line], last_line: int) -> int:
        width = args.width
        for line_number, runs in enumerate([] if args.wrap else lines, start=1):
            x = float(text_x)
            for _, text in runs:
                x = segment_width(text, x, text_x, font, args.tab_width)
                if x > MAX_LINE_WIDTH:
                    raise too_long(path, line_number)
            width = max(width, math.ceil(x + 44))
        if title_font:
            title = f"{path.name}  |  {language}  |  Lines {last_line}-{last_line}"
            width = max(width, math.ceil(47 + title_font.getlength(title) + 28))
        return width

    full_width = max(needed_width(path, language, lines, len(lines))
                     for path, language, lines in prepared)

    line_height, title_height, top_pad, bottom_pad = page_layout(args.font_size, args.header)
    pages = []
    for path, language, lines in prepared:
        for page_index in range(page_count_for(lines)):
            first = page_index * args.lines_per_image
            page_lines = lines[first:first + args.lines_per_image]
            width = (needed_width(path, language, page_lines, len(lines))
                     if args.fit_width else full_width)
            rows = None
            row_count = len(page_lines)
            if args.wrap:
                rows = [wrap_line(runs, text_x, width - 44, font, args.tab_width)
                        for runs in page_lines]
                for offset, line_rows in enumerate(rows):
                    if len(line_rows) > MAX_WRAPPED_ROWS:
                        raise too_long(path, first + offset + 1)
                row_count = sum(len(line_rows) for line_rows in rows)
            height = title_height + top_pad + line_height * row_count + bottom_pad
            if width * height > MAX_IMAGE_PIXELS:
                raise ValueError(
                    f"{path.name} lines {first + 1}-{first + len(page_lines)} would make a "
                    f"{width}×{height} px image, too large for most programs to open. "
                    "Use fewer lines per image, a smaller font size, or shorter lines.")
            pages.append((path, language, lines, page_index, first, page_lines, width, rows))

    def page_name(stem: str, page_number: int) -> str:
        if args.name_style == "padded":
            return f"{stem}_{page_number:03d}.png"
        return f"{stem}{page_number}.png"

    # Page names must not overwrite each other: "a" page 11 and "a1" page 1 are
    # both a11.png, and a1.png/A1.png are one file on macOS and Windows.
    stem_counts: Dict[str, int] = {}
    for path in files:
        stem_counts[path.stem.lower()] = stem_counts.get(path.stem.lower(), 0) + 1
    output_stems: Dict[Path, str] = {}
    used_names = set()
    for path, _, lines in prepared:
        numbers = range(1, page_count_for(lines) + 1)
        base = (path.stem if stem_counts[path.stem.lower()] == 1
                else f"{path.stem}_{path.suffix[1:].lower()}")
        stem = base
        suffix = 2
        while any(page_name(stem, n).lower() in used_names for n in numbers):
            stem = f"{base}_{suffix}"
            suffix += 1
        used_names.update(page_name(stem, n).lower() for n in numbers)
        output_stems[path] = stem
    args.output.mkdir(parents=True, exist_ok=True)
    guides = {path: structural_guides(language, lines, args.tab_width)
              for path, language, lines in prepared}
    for path, language, lines, page_index, first, page_lines, width, rows in pages:
        target = args.output / page_name(output_stems[path], page_index + 1)
        render_page(path, language, page_lines, first + 1, width,
                    line_digits, font, THEMES[args.theme], args.tab_width,
                    target, args.font_size, guides[path],
                    args.active_line, args.header, rows)
        print(f"{target}  (lines {first + 1}-{first + len(page_lines)})")
    total = len(pages)
    print(f"Created {total} PNG{'s' if total != 1 else ''} in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
