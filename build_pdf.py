#!/usr/bin/env python3
"""Build the print-edition PDF of Small-n Management from manuscript.md.

Two-pass process:
  1. Generate print.html with a placeholder table of contents, render with
     headless Chrome, and extract the page each section starts on.
  2. Regenerate with real TOC page numbers, render again, and verify that
     the section start pages did not move.

Output: small-n_management.pdf (6x9 in trade format).
"""

import html
import json
import re
import subprocess
import sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MANUSCRIPT = "manuscript.md"
PRINT_HTML = "print.html"
PDF = "small-n_management.pdf"

# Distinct opener text used to locate each section's first page in pass 1.
SECTION_MARKERS = {
    "Introduction: The Red Number": "born in a single monthly business review",
    "Chapter 1: Why Sample Size Changes Strategy": "The meeting that opened this book",
    "Chapter 2: Reasoning When Rates Lie": "The board meets Thursday",
    "Chapter 3: Decision-Making When You Can't Diversify": "The proposal is on the table",
    "Chapter 4: Building the System Before the Shock": "The worst number I have ever owned",
    "Chapter 5: Translating Small-n Upward": "The first four chapters built an operating system",
    "Conclusion: Choose Your Denominator": "Everything in this book reduces to three realities",
    "A Note on Examples": "draws on four kinds of material",
    "Notes": "These notes are deliberately light",
    "Statement on the Use of AI": "used extensively during the drafting and revision",
    "About the Author": "Peter Gratzke has held Innovation",
}


def smart_quotes(text):
    # Apostrophes inside words and possessives (don't, Vantage's, years')
    text = re.sub(r"(\w)'", r"\1’", text)
    # Opening quotes after start/whitespace/opening bracket, else closing.
    text = re.sub(r'(^|[\s(\[])"', "\\1“", text)
    text = text.replace('"', "”")
    text = re.sub(r"(^|[\s(\[])'", "\\1‘", text)
    text = text.replace("'", "’")
    return text


def inline(text):
    text = html.escape(smart_quotes(text), quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def split_title(title):
    """Return (label, display_title, running_head) for a section title."""
    m = re.match(r"(Chapter \d+): (.+)", title)
    if m:
        return m.group(1).upper(), m.group(2), m.group(2)
    m = re.match(r"(Conclusion): (.+)", title)
    if m:
        return "CONCLUSION", m.group(2), m.group(2)
    return None, title, title


def parse_manuscript():
    """Return list of (title, [content lines])."""
    sections = []
    current = None
    for line in open(MANUSCRIPT).read().split("\n"):
        if line.startswith("# "):
            current = (line[2:].strip(), [])
            sections.append(current)
        elif current is not None:
            current[1].append(line)
    return sections


CSS = """
@page { size: 6in 9in; margin: 0.85in 0.75in 0.9in 0.75in; }
@page coverpg { margin: 0; }
@page frontmatter { margin: 0.85in 0.75in 0.9in 0.75in; }
%(chapter_pages)s

* { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 10.5pt; }
body {
  font-family: Georgia, 'Times New Roman', serif;
  line-height: 1.62;
  color: #111;
  text-align: justify;
  hyphens: auto;
  -webkit-hyphens: auto;
  hyphenate-limit-chars: 7 4 3;
}

section.coverpage { page: coverpg; break-before: page; }
section.coverpage img { display: block; width: 6in; height: 9in; object-fit: cover; }

section.front { page: frontmatter; break-before: page; text-align: center; hyphens: none; }

.halftitle { padding-top: 2.6in; }
.halftitle h1 { font-size: 17pt; font-weight: normal; letter-spacing: 0.18em; text-transform: uppercase; }

.titlepage { padding-top: 2.1in; }
.titlepage h1 { font-size: 27pt; font-weight: bold; letter-spacing: 0.01em; }
.titlepage .subtitle { font-style: italic; font-size: 12pt; margin-top: 0.9em; color: #333; }
.titlepage .author { margin-top: 2.6in; font-size: 12.5pt; letter-spacing: 0.14em; text-transform: uppercase; }

.copyrightpage { height: 7.2in; display: flex; flex-direction: column; justify-content: flex-end;
                 align-items: center; font-size: 8.5pt; color: #333; line-height: 1.55; }
.copyrightpage p { margin-bottom: 0.6em; text-indent: 0; max-width: 4.6in; }

.tocpage { text-align: left; padding-top: 0.55in; }
.tocpage h1 { font-size: 15pt; letter-spacing: 0.14em; text-transform: uppercase; font-weight: normal; margin-bottom: 1.6em; text-align: center; }
.tocpage ol { list-style: none; }
.tocpage li { margin-bottom: 0.85em; font-size: 10.5pt; display: flex; align-items: baseline; }
.tocpage li .t { white-space: nowrap; }
.tocpage li .dots { flex: 1; border-bottom: 1px dotted #999; margin: 0 0.45em 0.22em 0.45em; }
.tocpage li .pg { font-variant-numeric: tabular-nums; }
.tocpage li.fm { color: #444; }

section.chapter { break-before: page; }
.tocpage a { color: inherit; text-decoration: none; }
.ch-label { text-align: center; font-size: 9pt; letter-spacing: 0.28em; color: #666; padding-top: 1.05in; text-indent: 0; }
section.chapter h1.ch-title { text-align: center; font-size: 19.5pt; font-weight: bold; line-height: 1.25; margin: 0.5em 1.2em 2.4em; hyphens: none; }
section.chapter.nolabel h1.ch-title { margin-top: 1.35in; }

h2 { font-size: 11.5pt; font-variant: small-caps; letter-spacing: 0.05em; font-weight: bold;
     text-align: left; margin: 1.7em 0 0.75em; break-after: avoid; hyphens: none; }
h2 + p { text-indent: 0; }

p { text-indent: 1.35em; orphans: 2; widows: 2; }
h1 + p, .ch-label + p, p.first { text-indent: 0; }
p:has(> strong:first-child) { text-indent: 0; margin-top: 0.55em; margin-bottom: 0.35em; }

ul { margin: 0.6em 0 0.9em 1.7em; }
li { margin-bottom: 0.25em; text-indent: 0; }

section.backmatter p, section.backmatter li { font-size: 9.2pt; line-height: 1.55; }
section.backmatter p { text-indent: 0; margin-bottom: 0.65em; }
"""

PAGE_TEMPLATE = """@page ch%(idx)d {
  margin: 0.85in 0.75in 0.9in 0.75in;
  @top-center { content: "%(head)s"; font-family: Georgia, serif; font-size: 7.5pt;
                letter-spacing: 0.22em; color: #777; }
  @bottom-center { content: counter(page); font-family: Georgia, serif; font-size: 9pt; color: #444; }
}
section.ch%(idx)d { page: ch%(idx)d; }
"""


def build_html(toc_pages):
    sections = parse_manuscript()

    page_rules, body, toc_entries = [], [], []
    backmatter_titles = {"A Note on Examples", "Notes", "Statement on the Use of AI"}

    for idx, (title, lines) in enumerate(sections):
        label, display, head = split_title(title)
        page_rules.append(PAGE_TEMPLATE % {"idx": idx, "head": html.escape(head.upper(), quote=True)})

        classes = f"chapter ch{idx}"
        if label is None:
            classes += " nolabel"
        if title in backmatter_titles:
            classes += " backmatter"
        part = [f'<section class="{classes}" id="s{idx}">']
        if label:
            part.append(f'<p class="ch-label">{label}</p>')
        part.append(f'<h1 class="ch-title">{inline(display)}</h1>')

        in_ul = False
        first_para = True
        for raw in lines:
            ls = raw.strip()
            if not ls:
                if in_ul:
                    part.append("</ul>")
                    in_ul = False
                continue
            if ls.startswith("## "):
                if in_ul:
                    part.append("</ul>")
                    in_ul = False
                part.append(f"<h2>{inline(ls[3:])}</h2>")
            elif ls.startswith("- "):
                if not in_ul:
                    part.append("<ul>")
                    in_ul = True
                part.append(f"<li>{inline(ls[2:])}</li>")
            else:
                if in_ul:
                    part.append("</ul>")
                    in_ul = False
                cls = ' class="first"' if first_para else ""
                part.append(f"<p{cls}>{inline(ls)}</p>")
                first_para = False
        if in_ul:
            part.append("</ul>")
        part.append("</section>")
        body.append("\n".join(part))

        pg = toc_pages.get(title, "")
        fm = ' class="fm"' if title in backmatter_titles or title == "About the Author" else ""
        toc_entries.append(
            f'<li{fm}><a class="t" href="#s{idx}">{inline(title)}</a>'
            f'<span class="dots"></span><span class="pg">{pg}</span></li>'
        )

    css = CSS % {"chapter_pages": "\n".join(page_rules)}
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Small-n Management</title>
<style>{css}</style>
</head>
<body>
<section class="coverpage"><img src="cover.png" alt="Cover"></section>

<section class="front halftitle"><h1>Small-n Management</h1></section>

<section class="front titlepage">
<h1>Small-n Management</h1>
<p class="subtitle">Managing When Averages Mislead, Forecasts Fail,<br>and Every Event Matters</p>
<p class="author">Peter Gratzke</p>
</section>

<section class="front copyrightpage">
<p>Copyright &copy; 2026 Peter Gratzke. All rights reserved.</p>
<p>No part of this publication may be reproduced or distributed in any form without permission from the author, except for brief quotations used in reviews or commentary.</p>
<p>Some names, identifying details, and figures have been changed; several cases are composites, as described in the note on examples at the back. Cases told under real names are drawn from the public record and cited in the Notes.</p>
<p>First edition, 2026. Set in Georgia.</p>
</section>

<section class="front tocpage">
<h1>Contents</h1>
<ol>
{chr(10).join(toc_entries)}
</ol>
</section>

{chr(10).join(body)}
</body>
</html>"""
    open(PRINT_HTML, "w").write(doc)


def render(src=PRINT_HTML, out=PDF):
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={out}", f"file://{sys.path[0] or '.'}/{src}"],
        check=True, capture_output=True, cwd=".",
    )


OVERLAY_HTML = "overlay.html"
OVERLAY_PDF = "overlay.pdf"


def make_head_overlay():
    """A 6x9 page whose only ink is a white bar over the running-head area.

    Chrome paints @page margin boxes above everything else, so the only way to
    suppress the running head on chapter-opening pages is to stamp over it in
    post-processing.
    """
    open(OVERLAY_HTML, "w").write(
        """<!DOCTYPE html><html><head><style>
@page { size: 6in 9in; margin: 0; }
body { margin: 0; }
div { width: 6in; height: 0.78in; background: #ffffff;
      -webkit-print-color-adjust: exact; print-color-adjust: exact; }
</style></head><body><div></div></body></html>"""
    )
    render(OVERLAY_HTML, OVERLAY_PDF)


def find_section_pages():
    from pypdf import PdfReader

    reader = PdfReader(PDF)
    pages = [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    found, cursor = {}, 0
    for title, marker in SECTION_MARKERS.items():
        for pno, text in pages[cursor:]:
            if marker in text.replace("’", "'").replace("“", '"').replace("”", '"'):
                found[title] = pno
                cursor = pno - 1
                break
        else:
            raise RuntimeError(f"marker not found for: {title}")
    return found, len(pages)


def main():
    import os
    os.chdir(sys.path[0] or ".")

    build_html({})
    render()
    pages_pass1, total1 = find_section_pages()

    build_html(pages_pass1)
    render()
    pages_pass2, total2 = find_section_pages()

    if pages_pass1 != pages_pass2 or total1 != total2:
        raise RuntimeError(f"page drift between passes: {pages_pass1} vs {pages_pass2}")

    add_outline_and_metadata(pages_pass2)

    print(f"OK: {total2} pages")
    print(json.dumps(pages_pass2, indent=1))


def add_outline_and_metadata(section_pages):
    import os

    from pypdf import PdfReader, PdfWriter

    make_head_overlay()
    overlay = PdfReader(OVERLAY_PDF).pages[0]

    reader = PdfReader(PDF)
    writer = PdfWriter()
    writer.append(reader)
    for pno in section_pages.values():
        writer.pages[pno - 1].merge_page(overlay)
    os.remove(OVERLAY_HTML)
    os.remove(OVERLAY_PDF)
    writer.add_metadata({
        "/Title": "Small-n Management: Managing When Averages Mislead, Forecasts Fail, and Every Event Matters",
        "/Author": "Peter Gratzke",
        "/Subject": "Decision-making and evidence in small-sample, high-stakes business environments",
    })
    writer.add_outline_item("Cover", 0)
    for title, pno in section_pages.items():
        writer.add_outline_item(title, pno - 1)
    with open(PDF, "wb") as f:
        writer.write(f)


if __name__ == "__main__":
    main()
