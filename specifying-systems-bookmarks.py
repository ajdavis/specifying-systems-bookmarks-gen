#!/usr/bin/env python3
"""
Generate a Table of Contents for "Specifying Systems".

The "Specifying Systems" book by Leslie Lamport is distributed as a PDF without
any "bookmarks" (locations in the PDF that appear in the sidebar of e.g.
Preview.app): lamport.azurewebsites.net/tla/book.html. This script is a hacky
but automated means to create a version of the PDF with bookmarks.

Requires Python 3.8+ and the packages listed in requirements.txt.
"""
import re
from dataclasses import dataclass
from subprocess import check_call, check_output

# TODO: argparse
BOOK_PDF = "book-21-07-04.pdf"

# Create a recipe file using pdfxmeta, part of pdf.tocgen. Each of the strings
# below is a chapter/section/etc. heading. The recipe file will contain font
# attributes of those strings, so we can find all similar such strings and
# consider them headings. The levels don't work (chapters, sections, etc. have
# the same font in "Specifying Systems") so we'll process them further below.
with open('recipe.toml', 'w+') as recipe_file:
    # Create the recipe.
    for pageno, level, pattern in [
        (9, 1, "Contents"),
        (23, 2, "Part I"),
        (23, 3, "Getting Started"),
        (27, 4, "A Little Simple Math"),
        (27, 5, "Propositional Logic"),
    ]:
        output = check_output(
            ['pdfxmeta', '-p', str(pageno), '-a', str(level), BOOK_PDF,
             pattern], text=True)
        recipe_file.write(output)
        recipe_file.write('\n')

# Create the raw Table Of Contents (TOC). Since different heading levels in
# "Specifying Systems" aren't sufficiently distinguished by font, we'll have to
# do some more munging.
toc_raw = check_output(['pdftocgen', '-v', '-r', 'recipe.toml', BOOK_PDF],
                       text=True)


@dataclass
class RawTOCLine:
    title: str
    page: int
    vertical_position: float
    level: int = 0

    def to_toc_line(self):
        spaces = ' ' * 4 * self.level
        return f'{spaces}"{self.title}" {self.page} {self.vertical_position}'


def gen_bookmarks():
    buffer = None

    for line_text in toc_raw.split('\n'):
        if not line_text.strip():
            continue

        line_match = re.match(r'(\s*)"(.*?)" (\d+) ([\d.]+)', line_text)
        line = RawTOCLine(title=line_match.group(2),
                          page=int(line_match.group(3)),
                          vertical_position=float(line_match.group(4)))

        # In "Specifying Systems", a part/chapter begins like:
        #
        #           Part I
        #       Getting Started
        #
        # pdftocgen makes 2 lines in toc_raw. Buffer the first line, add it to
        # the second to produce a bookmark titled "Part I - Getting Started".
        if title_match := re.search(r'"(Part \w+)"', line.title):
            buffer = title_match.group(0)
        elif title_match := re.search(r'"(Chapter \d+)"', line.title):
            buffer = title_match.group(0)
        elif buffer:
            # If buffer starts with 'Chapter' then indent one level, otherwise
            # it's a Part which is higher-level and not indented.
            line.level = 1 if buffer.startswith('Chapter') else 0
            line.title = f'{buffer} - {line.title}'
            buffer = None
            yield line
        else:
            # Not a chapter or part header. If it's front matter before Part I,
            # no indent, otherwise it's a section header beneath a chapter.
            line.level = 0 if part == 0 else 2
            yield line


with open('toc.tmp', 'w+') as toc_file:
    part = chapter = 0
    buffer = None
    for line in toc_raw.split('\n'):
        if not line.strip():
            continue

        if line == "Specifying Systems":
            continue

        line_groups = re.match(r'(\s*)"(.*?)" (\d+) ([\d.]+)', line)
        spaces = line_groups.group(1)
        indents = len(spaces) // 2
        title = line_groups.group(2)
        page = line_groups.group(3)
        vert = line_groups.group(4)

        if level == 5 and (match := re.search(r'"Part (\w+)"', line)):
            part = match.group(1)
            buffer = f'Part {part}'
        elif level == 5 and (match := re.search(r'"Chapter (\d+)"', line)):
            chapter = match.group(1)
            buffer = f'Chapter {chapter}'
        elif buffer:
            new_spaces = '    ' if buffer.startswith('Chapter') else ''
            toc_file.write(f'{new_spaces}"{buffer} - {title}" {page} {vert}\n')
            buffer = None
        else:
            new_spaces = '' if part == 0 else '        '
            toc_file.write(f'{new_spaces}"{title}" {page} {vert}\n')

check_call(['pdftocio', BOOK_PDF, '-t', 'toc.tmp'])
