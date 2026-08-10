#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf2md.py — Convert a PDF book into a single Markdown document (with images).

Usage:
    python3 pdf2md.py <input.pdf> [-o output_dir]

Default behaviour (no -o):
    input  book.pdf
    output book/                      # folder named after the PDF (same directory)
        ├── book.pdf                  # original PDF (copied, self-contained archive)
        ├── book.md                   # the converted single Markdown file
        └── images/                   # extracted figures (image_0001.png ...)

Output convention follows epub2md: one merged .md + one images/ folder + a
same-named output folder.

This tool is tuned for *illustrated* technical books (especially CJK / 中文
books) where most figures are vector drawings that must be *rendered* rather
than merely extracted as embedded bitmaps.
"""
import os
import re
import sys
import time
import argparse
import io
import shutil
import fitz                      # PyMuPDF
from PIL import Image

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
# Optional: running-header / footer strings to suppress. Safe to leave empty;
# only matches exact substrings. Extend with your book's repeating footer.
FOOTER_SUB = (
    "Hands-On Large Language Models",
    "O’Reilly Media, Inc.",
    "O'Reilly Media, Inc.",
)

# Short "label" headings that are not real section titles -> demoted to bold
# paragraphs (mirrors epub2md's normalize_fake_headings).
LABEL_SET = {"输出", "结果", "输入", "注意", "提示", "警告", "说明", "指令", "命令",
             "示例", "代码", "RAG", "API", "提供示例", "采样输出", "提供", "采样"}

MONO_KW = ("mono", "courier", "consol", "code", "menlo", "sfmono", "dejavu")
CJK = re.compile(r"[\u4e00-\u9fff]")
NUM_HEAD = re.compile(r"^\s*(\d+(\.\d+){1,3})\b")
CHAP_HEAD = re.compile(r"^第\s*\d+\s*章")
PART_HEAD = re.compile(r"^第.部分|^Part\b|^\s*Part\s", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_cjk(text):
    text = text.replace(" ", "")
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[A-Za-z0-9])", "", text)
    text = re.sub(r"(?<=[A-Za-z0-9])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def is_mono(fontname):
    if not fontname:
        return False
    f = fontname.lower()
    return any(k in f for k in MONO_KW)


def compute_body_size(doc):
    sizes = {}
    for i in range(doc.page_count):
        for b in doc[i].get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    sz = round(s["size"])
                    sizes[sz] = sizes.get(sz, 0) + 1
    return float(max(sizes, key=lambda k: sizes[k])) if sizes else 10.0


def cluster_drawings(drawings, gap=22):
    rects = [d["rect"] for d in drawings if d.get("rect")]
    rects.sort(key=lambda r: (r.y0, r.x0))
    clusters = []
    for r in rects:
        placed = False
        for c in clusters:
            if (abs(r.y0 - c["y1"]) <= gap) and (r.x0 >= c["x0"] - 25) and (r.x1 <= c["x1"] + 25):
                c["y1"] = max(c["y1"], r.y1)
                c["x0"] = min(c["x0"], r.x0)
                c["x1"] = max(c["x1"], r.x1)
                placed = True
                break
        if not placed:
            clusters.append({"y0": r.y0, "y1": r.y1, "x0": r.x0, "x1": r.x1})
    return clusters


def get_chapters(doc):
    """Top-level outline entries -> [(start_page_1based, title), ...]."""
    toc = doc.get_toc()
    if not toc:
        return []
    min_level = min(level for level, _, _ in toc)
    return [(page, title.strip()) for level, title, page in toc if level == min_level]


def current_chapter(chapters, page_no):
    cur = None
    for start, title in chapters:
        if start <= page_no:
            cur = (start, title)
        else:
            break
    return cur


def extract_page(doc, page_no, body_size, img_dir, counter, stats, fig_bboxes):
    """Return items: (y0, x0, kind, data). fig_bboxes is filled with figure rects."""
    page = doc[page_no - 1]
    dict_ = page.get_text("dict")
    drawings = page.get_drawings()
    items = []

    # 1) Vector drawings -> render to PNG
    for c in cluster_drawings(drawings):
        w = c["x1"] - c["x0"]
        h = c["y1"] - c["y0"]
        if w < 28 or h < 28:
            continue
        bbox = fitz.Rect(c["x0"], c["y0"], c["x1"], c["y1"])
        chars = 0
        mono = False
        for b in dict_.get("blocks", []):
            if b.get("type") != 0:
                continue
            bb = fitz.Rect(b["bbox"])
            if bb.y1 < bbox.y0 or bb.y0 > bbox.y1 or bb.x1 < bbox.x0 or bb.x0 > bbox.x1:
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    chars += len(s["text"])
                    if is_mono(s["font"]):
                        mono = True
        if mono or chars > 400:        # code / body text region -> keep text
            continue
        try:
            pix = page.get_pixmap(clip=bbox, dpi=150, alpha=False)
        except Exception:
            continue
        if pix.width < 40 or pix.height < 40:
            continue
        if max(pix.width, pix.height) < 110:   # skip tiny decorative icons
            continue
        counter[0] += 1
        fname = f"image_{counter[0]:04d}.png"
        pix.save(os.path.join(img_dir, fname))
        stats["vector"] += 1
        items.append((bbox.y0, bbox.x0, "image", f"images/{fname}"))
        fig_bboxes.append(bbox)

    # 2) Embedded raster images
    for b in dict_.get("blocks", []):
        if b.get("type") != 1:
            continue
        img_bytes = b.get("image")
        x0, y0, x1, y1 = b["bbox"]
        w = x1 - x0
        h = y1 - y0
        if not img_bytes or w < 30 or h < 30:
            continue
        try:
            im = Image.open(io.BytesIO(img_bytes))
            iw, ih = im.size
        except Exception:
            continue
        if iw > 8000 or ih > 8000:
            continue
        if max(iw, ih) < 110:
            continue
        if im.mode == "CMYK":          # fix unreadable CMYK previews
            im = im.convert("RGB")
        counter[0] += 1
        fname = f"image_{counter[0]:04d}.png"
        im.save(os.path.join(img_dir, fname))
        stats["raster"] += 1
        items.append((y0, x0, "image", f"images/{fname}"))
        fig_bboxes.append(fitz.Rect(b["bbox"]))

    def inside_fig(bbox):
        for fb in fig_bboxes:
            ix0 = max(bbox.x0, fb.x0)
            iy0 = max(bbox.y0, fb.y0)
            ix1 = min(bbox.x1, fb.x1)
            iy1 = min(bbox.y1, fb.y1)
            if ix1 > ix0 and iy1 > iy0:
                inter = (ix1 - ix0) * (iy1 - iy0)
                area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0)
                if area > 0 and inter / area > 0.6:
                    return True
        return False

    # 3) Text / code / headings
    for b in dict_.get("blocks", []):
        if b.get("type") != 0:
            continue
        bbox = fitz.Rect(b["bbox"])
        if inside_fig(bbox):
            continue
        lines_txt = []
        block_mono = False
        max_sz = 0
        for l in b.get("lines", []):
            line_text = ""
            for s in l.get("spans", []):
                line_text += s["text"]
                if is_mono(s["font"]):
                    block_mono = True
                max_sz = max(max_sz, s["size"])
            lines_txt.append(line_text)
        raw = "\n".join(lines_txt).strip()
        if not raw:
            continue
        cleaned = []
        for ln in raw.splitlines():
            ls = ln.strip()
            if not ls:
                continue
            if any(sub in ls for sub in FOOTER_SUB):
                continue
            if re.fullmatch(r"\d{1,3}", ls):          # isolated page number
                continue
            if re.search(r"[｜|]\s*\d{1,3}\s*$", ls) and len(ls) <= 40:
                continue
            if re.fullmatch(r"\d{1,3}\s*[｜|]\s*.{1,30}", ls):
                continue
            cleaned.append(ls)
        if not cleaned:
            continue
        text = "\n".join(cleaned)
        if block_mono:
            items.append((bbox.y0, bbox.x0, "code", text))
            continue
        size_ratio = max_sz / body_size if body_size else 1
        is_head = (size_ratio >= 1.32 and len(text) <= 50
                   and not text.endswith(("。", "，", "；", "：", ")", "）", ".", ",")))
        if is_head:
            m = NUM_HEAD.match(text)
            dots = text.strip().split()[0].count(".") if m else None
            items.append((bbox.y0, bbox.x0, "heading", (clean_cjk(text), dots)))
        else:
            # Chinese code comments (start with #, rendered in a CJK font) -> code
            if text.strip().startswith("#"):
                items.append((bbox.y0, bbox.x0, "code", text))
                continue
            txt = clean_cjk(text)
            txt = re.sub(r"(?m)^[•·]\s*", "- ", txt)
            items.append((bbox.y0, bbox.x0, "text", txt))

    items.sort(key=lambda it: (round(it[0], 1), it[1]))
    return items


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="PDF -> single Markdown (with images/)")
    ap.add_argument("pdf", nargs="?", default=None, help="input PDF path")
    ap.add_argument("-o", "--output", default=None, help="output folder (default: <pdf-dir>/<pdf-stem>)")
    args = ap.parse_args()

    # Resolve input PDF
    pdf_path = args.pdf
    if not pdf_path:
        cands = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
        if len(cands) == 1:
            pdf_path = cands[0]
            print(f"no PDF given; using {pdf_path}")
        else:
            ap.error("provide a PDF path, or place exactly one .pdf in the current directory")

    if not os.path.isfile(pdf_path):
        ap.error(f"file not found: {pdf_path}")

    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = args.output or os.path.join(os.path.dirname(os.path.abspath(pdf_path)), stem)
    md_path = os.path.join(out_dir, f"{stem}.md")
    img_dir = os.path.join(out_dir, "images")

    # Fresh output (avoid stale images from a previous run).
    # Deletion may be blocked in some sandboxed environments; if so we just
    # continue and overwrite — any leftover files are harmless.
    if os.path.exists(img_dir):
        try:
            shutil.rmtree(img_dir)
        except Exception as e:
            print(f"warning: could not clear {img_dir} ({e}); reusing it")
    os.makedirs(img_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    body_size = compute_body_size(doc)
    meta_title = (doc.metadata or {}).get("title", "") or ""
    book_title = meta_title.strip() or stem
    chapters = get_chapters(doc)
    print(f"title={book_title!r}; body_size={body_size}; chapters={len(chapters)}; -> {out_dir}")

    counter = [0]
    stats = {"vector": 0, "raster": 0}
    t0 = time.time()

    lines = [f"# {book_title}", "", "---", ""]
    first_h2 = [True]

    def emit_heading(level, text):
        if level == 2:
            if first_h2[0]:
                first_h2[0] = False
                lines.append("")
                lines.append(f"## {text}")
                lines.append("")
            else:
                lines.append("---")
                lines.append("")
                lines.append(f"## {text}")
                lines.append("")
        else:
            lines.append("")
            lines.append(f"{'#' * level} {text}")
            lines.append("")

    for page_no in range(1, doc.page_count + 1):
        fig_bboxes = []
        items = extract_page(doc, page_no, body_size, img_dir, counter, stats, fig_bboxes)
        if not items:
            continue
        ch = current_chapter(chapters, page_no)
        chap_title = ch[1] if ch else ""
        if ch and page_no == ch[0]:
            emit_heading(2, chap_title)
        buf_code = []

        def flush_code():
            if buf_code:
                lines.append("")
                # 4-backtick fence: avoids collision when source code itself
                # contains a ``` line (e.g. prompt/JSON templates).
                lines.append("````python")
                lines.append("\n".join(buf_code))
                lines.append("````")
                lines.append("")
                buf_code.clear()

        prev = None
        for y0, x0, kind, data in items:
            if kind == "text":
                flush_code()
                if prev not in (None, "text"):
                    lines.append("")
                lines.append(data)
                lines.append("")
                prev = "text"
            elif kind == "code":
                buf_code.append(data)
                prev = "code"
            elif kind == "image":
                flush_code()
                if prev is not None:
                    lines.append("")
                lines.append(f"![图]({data})")
                lines.append("")
                prev = "image"
            elif kind == "heading":
                flush_code()
                text, dots = data
                # Skip duplicates / part titles / punctuation-only fakes
                if CHAP_HEAD.match(text) or text == chap_title or (chap_title and text in chap_title):
                    prev = "heading"
                    continue
                if PART_HEAD.match(text):
                    prev = "heading"
                    continue
                ts = text.strip()
                if len(ts) <= 1 or re.fullmatch(r"[\W_]+", ts):
                    prev = "heading"
                    continue
                if ts in LABEL_SET or re.match(r"^(提供|采样|输出|输入|示例|注意|提示|说明|指令|代码|结果)\S*$", ts):
                    lines.append("")
                    lines.append(f"**{text}**")
                    lines.append("")
                    prev = "heading"
                    continue
                if dots is not None:
                    lvl = min(dots + 2, 6)      # 1.1 -> H3, 1.1.1 -> H4
                else:
                    lvl = 3                       # unnumbered subsection -> H3
                emit_heading(lvl, text)
                prev = "heading"
        flush_code()

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    # Copy the original PDF into the output folder (self-contained archive)
    try:
        shutil.copy2(pdf_path, os.path.join(out_dir, os.path.basename(pdf_path)))
    except Exception as e:
        print(f"warning: could not copy source PDF: {e}")

    print(f"done: {counter[0]} images ({stats['vector']} vector + {stats['raster']} raster) "
          f"in {time.time() - t0:.1f}s -> {md_path}")


if __name__ == "__main__":
    main()
