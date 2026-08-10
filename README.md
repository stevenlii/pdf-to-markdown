# pdf-to-markdown

Convert a PDF book into a **single Markdown document** plus an `images/` folder.
Inspired by [`epub2md`](https://github.com/stevenlii/epub2md).

It is tuned for **illustrated technical books** — especially CJK / 中文 books —
where most figures are **vector drawings** that must be *rendered* to images,
rather than merely pulled out as embedded bitmaps.

---

## Features

- **One merged `.md`** with a clean heading hierarchy:
  - `#` — book title (taken from the PDF metadata)
  - `##` — chapters (taken from the PDF's table of contents / outline)
  - `###` / `####` — numbered sections (`1.1`, `1.1.1`, …)
- **Vector figures rendered** with PyMuPDF `get_drawings()` → PNG.
- **Embedded raster images extracted** (CMYK → RGB fix so they preview correctly).
- **Code blocks detected** by monospaced font and fenced with **4 backticks**
  (```` ```python ````) so source that itself contains ```` ``` ```` lines
  (e.g. prompt / JSON templates) does not break the fence. Chinese `#` comments
  that would otherwise be misread as headings are also captured as code.
- **CJK spacing cleaned**; running headers/footers and page numbers filtered out.
- **Tiny decorative icons skipped.**
- **Source PDF copied** into the output folder for a self-contained archive.

## Requirements

- Python **3.8+**
- [`pymupdf`](https://pymupdf.readthedocs.io/) (bundles MuPDF — no extra system
  libraries on macOS / Windows; works headless on Linux / CentOS)

That is the *only* third-party dependency.

## Installation

### Isolated virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### macOS

```bash
brew install python              # if Python 3.8+ is not already present
python3 -m venv .venv && source .venv/bin/activate
pip install pymupdf
```

### Windows

```powershell
# Install Python from python.org, or:  winget install Python.Python.3.12
python -m venv .venv
.venv\Scripts\activate
pip install pymupdf
```

### CentOS / RHEL

```bash
sudo yum install python3 python3-pip      # or: sudo dnf install ...
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install pymupdf
```

> Tip: on a shared server you may prefer a user install instead of a venv:
> `pip install --user pymupdf`, then run with `python3 pdf2md.py …`.

## Usage

```bash
python pdf2md.py path/to/book.pdf
# optional explicit output folder:
python pdf2md.py book.pdf -o output_dir
```

If you omit the PDF argument, the script uses the single `.pdf` found in the
current directory (handy for quick runs).

## Output structure

Given `book.pdf`, the script creates a folder named `book/` containing:

```
book/
├── book.pdf          # original PDF (copied)
├── book.md           # the converted Markdown
└── images/           # extracted figures (image_0001.png …)
```

- `book.md` references images as `images/image_0001.png` — open it in
  **Obsidian** or any Markdown viewer.
- Chapters from the PDF outline become `##` headings; numbered sections become
  `###` / `####`.
- Code blocks are fenced.

## Examples

The `examples/` folder ships a tiny, **self-authored, copyright-free** sample PDF
and its `pdf2md` output, so you can see the tool work out of the box:

```
examples/
├── make_sample.py     # regenerates sample.pdf (needs a system CJK font)
├── sample.pdf         # the self-authored sample input
└── sample/            # pdf2md output:
    ├── sample.pdf     # original (copied)
    ├── sample.md      # converted Markdown
    └── images/        # extracted figures
```

To regenerate it yourself:

```bash
cd examples
python make_sample.py          # creates sample.pdf
python ../pdf2md.py sample.pdf # creates sample/
```

> The sample is original demo content, **not** a real book, so it is safe to
> redistribute. Do not commit converted output of copyrighted books.

## Notes / tuning

- **Chapter detection** uses the PDF's outline (table of contents). Books
  *without* a TOC will not be split into `##` chapters — headings are still
  detected by font size.
- The heading / font-size heuristics and the running-footer filter
  (`FOOTER_SUB` in `pdf2md.py`) are best-effort. Extend `FOOTER_SUB` with your
  book's repeating footer string if any slips through.
- Figures are rendered at **150 DPI**; change `dpi` in `extract_page()` if you
  need higher resolution.
- For very large books the conversion is single-threaded; a 400-page book
  typically finishes in under a minute.

## Credits

Output convention inspired by
[`epub2md`](https://github.com/stevenlii/epub2md). The figure-rendering
approach targets vector-heavy "图解" (illustrated) books.

## License

MIT — see `LICENSE` if you add one.
