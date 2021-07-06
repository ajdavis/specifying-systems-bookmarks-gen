#!/usr/bin/env python3
"""Generate bookmarks for each part/chapter/section of "Specifying Systems".

The "Specifying Systems" book by Leslie Lamport is distributed as a PDF without
any "bookmarks" (locations in the PDF that appear in the sidebar of e.g.
Preview.app): lamport.azurewebsites.net/tla/book.html. This script is a hacky
but automated means to create a version of the PDF with bookmarks.

Requires Python 3.8+ and the packages listed in requirements.txt.

The structure of the book is:

    Introductory Section 1
    Introductory Section 2
      .
      .
    Part I - <title>
        Chapter 1 - <title>
            1.1 - <title>
              .
              .
            1.n - <title>
          .
          .
    Part II - <title>
      .
      .
    Index

Limitation: clicking on the headings in the PDF's own table of contents won't
jump to the contents. Only clicking in the bookmarks view in e.g. Preview.app's
sidebar will navigate to the proper location.
"""
import argparse
import os
import re
import sys
from dataclasses import dataclass
from subprocess import check_call, check_output

parser = argparse.ArgumentParser(sys.argv[0],
                                 description=__doc__.split('\n')[0])

parser.add_argument('input_pdf', metavar='INPUT_PDF',
                    help='Path to a copy of "Specifying Systems"')
args = parser.parse_args()
output_pdf = f'{os.path.splitext(args.input_pdf)[0]}_out.pdf'

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
            ['pdfxmeta', '-p', str(pageno), '-a', str(level), args.input_pdf,
             pattern], text=True)
        recipe_file.write(output)
        recipe_file.write('\n')

# Create the raw Table Of Contents (TOC). Since different heading levels in
# "Specifying Systems" aren't sufficiently distinguished by font, we'll have to
# do some more munging.
toc_raw = check_output(['pdftocgen', '-v', '-r', 'recipe.toml', args.input_pdf],
                       text=True)


@dataclass
class TOCLine:
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
        line = TOCLine(title=line_match.group(2),
                       page=int(line_match.group(3)),
                       vertical_position=float(line_match.group(4)))

        if line.title == 'Specifying Systems':
            continue

        # In "Specifying Systems", a part/chapter begins like:
        #
        #           Part I
        #       Getting Started
        #
        # pdftocgen makes 2 lines in toc_raw, so we'll first see "Part I" and
        # then "Getting Started". Buffer the first line, add it to the second to
        # produce a bookmark titled "Part I - Getting Started".
        if title_match := re.search(r'Part (\w+)', line.title):
            buffer = title_match.group(0)
        elif title_match := re.search(r'Chapter \d+', line.title):
            buffer = title_match.group(0)
        elif re.search(r'(\d+)\.(\d+)\s+(\w+)', line.title):
            # This is a section like "1.2 Sets".
            assert buffer is None
            line.level = 2
            yield line
        elif buffer:
            # If buffer starts with 'Part' then this is top-level, else it's
            # 'Chapter' and this is level 1.
            line.level = 0 if buffer.startswith('Part') else 1
            line.title = f'{buffer} - {line.title}'
            buffer = None
            yield line
        else:
            # Not part, chapter, or section header. Accept default level 0.
            yield line


with open('toc.tmp', 'w+') as toc_file:
    introduction_page = None
    for toc_line in gen_bookmarks():
        if toc_line.title == "Introduction":
            # We'll use this below.
            introduction_page = toc_line.page

        toc_file.write(toc_line.to_toc_line() + '\n')

check_call(['pdftocio', args.input_pdf, '-t', 'toc.tmp', '-o', output_pdf])

# The first 18 pages of "Specifying Systems" are Roman-numeraled, and page 1
# starts around the 19th. Note this in PDF metadata so apps' "jump to page"
# feature works.
assert introduction_page is not None, "Couldn't find 'Introduction' page"

with open(output_pdf, 'rb+') as output_file:
    output_bytes = output_file.read()
    output_file.truncate(0)

    # The output PDF has one Catalog entry like:
    # <</Type/Catalog/Pages 1412 0 R/Outlines 1415 0 R>>
    # Add /PageLabels before /Outlines.
    n_catalogs = 0

    def replace_catalog(match):
        global n_catalogs
        n_catalogs += 1
        catalog_start = match.group(1).decode()
        catalog_end = match.group(2).decode()
        for catalog_part in catalog_start, catalog_end:
            assert '/PageLabels' not in catalog_part, \
                f'PDF already has PageLabels in Category: {catalog_part}'

        return f'''<<
{catalog_start}
/PageLabels << /Nums [ 0 << /S /r >> % start numbering in small Roman numerals
                       18 << /S /D >> % page 19 and onward in Arabic decimals
                     ]
            >>
{catalog_end}
>>'''.encode()

    output_file.write(re.sub(
        rb'<<([\s\n]*/Type[\s\n]*/Catalog.*)(/Outlines.*)>>',
        replace_catalog, output_bytes, flags=re.MULTILINE))
    assert n_catalogs > 0, f"Couldn't find /Catalog in {output_pdf}"
    assert n_catalogs == 1, f"Too many catalog entries in {output_pdf}"

print(output_pdf)
