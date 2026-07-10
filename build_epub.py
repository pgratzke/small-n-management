#!/usr/bin/env python3
"""Build the Kindle/EPUB edition of Small-n Management from manuscript.md.

Produces an EPUB 3 file (one XHTML document per top-level section, plus a
title page and embedded cover) suitable for upload to KDP. Typography
matches the print edition: smart quotes, no page furniture.

Output: small-n_management.epub
"""

import html
import re
import uuid
import zipfile

MANUSCRIPT = "manuscript.md"
EPUB = "small-n_management.epub"
COVER = "cover.png"

TITLE = "Small-n Management"
SUBTITLE = "Managing When Averages Mislead, Forecasts Fail, and Every Event Matters"
AUTHOR = "Peter Gratzke"
LANG = "en"


def smart_quotes(text):
    # Apostrophes inside words and possessives (don't, Vantage's, years')
    text = re.sub(r"(\w)'", r"\1’", text)
    # Opening quotes after start/whitespace/opening bracket, else closing.
    text = re.sub(r'(^|[\s(\[])"', "\\1“", text)
    text = text.replace('"', "”")
    text = re.sub(r"(^|[\s(\[])'", "\\1‘", text)
    text = text.replace("'", "’")
    return text


def inline(t):
    t = html.escape(smart_quotes(t), quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


# ---- parse manuscript into sections -----------------------------------

sections = []  # (title, [body html lines])
body = None
in_ul = False


def close_ul():
    global in_ul
    if in_ul:
        body.append("</ul>")
        in_ul = False


for line in open(MANUSCRIPT).read().split("\n"):
    ls = line.strip()
    if not ls:
        if body is not None:
            close_ul()
        continue
    if ls.startswith("# "):
        if body is not None:
            close_ul()
        body = []
        sections.append((ls[2:].strip(), body))
    elif ls.startswith("## "):
        close_ul()
        body.append(f"<h2>{inline(ls[3:].strip())}</h2>")
    elif ls.startswith("- "):
        if not in_ul:
            body.append("<ul>")
            in_ul = True
        body.append(f"<li>{inline(ls[2:].strip())}</li>")
    else:
        close_ul()
        body.append(f"<p>{inline(ls)}</p>")
close_ul()

# ---- assemble EPUB ------------------------------------------------------

CSS = """\
body { font-family: serif; line-height: 1.5; margin: 0 5%; }
h1 { font-size: 1.5em; text-align: left; margin: 2em 0 1.5em; line-height: 1.25; }
h2 { font-size: 1.15em; margin: 1.8em 0 0.6em; line-height: 1.3; }
p { margin: 0; text-indent: 1.4em; text-align: justify; }
h1 + p, h2 + p, ul + p { text-indent: 0; }
ul { margin: 0.8em 0; }
li { margin: 0.3em 0; }
.titlepage { text-align: center; margin-top: 20%; }
.titlepage h1 { text-align: center; font-size: 2em; margin-bottom: 0.3em; }
.titlepage .subtitle { font-style: italic; text-indent: 0; text-align: center; margin: 0 8%; }
.titlepage .author { text-indent: 0; text-align: center; margin-top: 3em; font-size: 1.1em; }
"""


def xhtml(title, content):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{LANG}">\n'
        f"<head><title>{html.escape(title)}</title>"
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        f"<body>\n{content}\n</body>\n</html>\n"
    )


cover_page = xhtml(
    TITLE,
    '<figure style="text-align:center;margin:0">'
    f'<img src="cover.png" alt="{html.escape(TITLE)}" '
    'style="max-width:100%;max-height:100%"/></figure>',
)

title_page = xhtml(
    TITLE,
    '<div class="titlepage">'
    f"<h1>{html.escape(TITLE)}</h1>"
    f'<p class="subtitle">{html.escape(SUBTITLE)}</p>'
    f'<p class="author">{html.escape(AUTHOR)}</p></div>',
)

docs = []  # (filename, display title, xhtml)
for i, (title, lines) in enumerate(sections, 1):
    content = f"<h1>{inline(title)}</h1>\n" + "\n".join(lines)
    docs.append((f"sec{i:02d}.xhtml", title, xhtml(title, content)))

nav_items = "\n".join(
    f'<li><a href="{fn}">{html.escape(t)}</a></li>' for fn, t, _ in docs
)
nav = xhtml(
    "Contents",
    '<nav epub:type="toc" id="toc"><h1>Contents</h1>\n'
    f"<ol>\n{nav_items}\n</ol>\n</nav>",
)

book_id = f"urn:uuid:{uuid.uuid4()}"
manifest = [
    '<item id="cover-image" href="cover.png" media-type="image/png" properties="cover-image"/>',
    '<item id="css" href="style.css" media-type="text/css"/>',
    '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
    '<item id="coverpage" href="coverpage.xhtml" media-type="application/xhtml+xml"/>',
    '<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>',
]
spine = [
    '<itemref idref="coverpage" linear="no"/>',
    '<itemref idref="titlepage"/>',
    '<itemref idref="nav"/>',
]
for i, (fn, _, _) in enumerate(docs, 1):
    manifest.append(
        f'<item id="sec{i:02d}" href="{fn}" media-type="application/xhtml+xml"/>'
    )
    spine.append(f'<itemref idref="sec{i:02d}"/>')

opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{LANG}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{book_id}</dc:identifier>
<dc:title id="t1">{html.escape(TITLE)}</dc:title>
<meta refines="#t1" property="title-type">main</meta>
<dc:title id="t2">{html.escape(SUBTITLE)}</dc:title>
<meta refines="#t2" property="title-type">subtitle</meta>
<dc:creator>{html.escape(AUTHOR)}</dc:creator>
<dc:language>{LANG}</dc:language>
<meta property="dcterms:modified">2026-07-10T00:00:00Z</meta>
</metadata>
<manifest>
{chr(10).join(manifest)}
</manifest>
<spine>
{chr(10).join(spine)}
</spine>
</package>
"""

container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
</rootfiles>
</container>
"""

with zipfile.ZipFile(EPUB, "w") as z:
    z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
    z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr("OEBPS/style.css", CSS, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr("OEBPS/coverpage.xhtml", cover_page, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr("OEBPS/titlepage.xhtml", title_page, compress_type=zipfile.ZIP_DEFLATED)
    z.write(COVER, "OEBPS/cover.png")
    for fn, _, doc in docs:
        z.writestr(f"OEBPS/{fn}", doc, compress_type=zipfile.ZIP_DEFLATED)

print(f"{EPUB}: {len(docs)} sections")
