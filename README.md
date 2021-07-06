# Generate Bookmarks & Page Numbers for "Specifying Systems"

The "Specifying Systems" book by Leslie Lamport
[is distributed as a PDF](https://lamport.azurewebsites.net/tla/book.html) without any "bookmarks"
(locations in the PDF that appear in the sidebar of e.g. Preview.app). This script is a hacky but
automated means to create a version of the PDF with bookmarks. It also renumbers pages so that the
introductory pages are Roman-numeraled like "xvi", and pages are labeled with Arabaic numbers
starting with the Introduction. This makes the "go to page" feature of Preview.app etc. accurate.

Requires Python 3.8+ and the packages listed in requirements.txt. You must download the book first
and run:
```
python3 specifying-systems-bookmarks.py <path to PDF>
```
