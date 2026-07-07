#!/usr/bin/env python3
"""Regenerate book.html (web layout) from manuscript.md, preserving the shell."""

import html
import re


def slug(t):
    s = re.sub(r"[^\w\s-]", "", t.lower())
    return re.sub(r"\s+", "-", s.strip())


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


md = open("manuscript.md").read()
old = open("book.html").read()
shell = old[: old.index('<nav class="toc">')]
footer = "\n</div>\n</body>\n</html>"

chapters, body, in_ul = [], [], False


def close_ul():
    global in_ul
    if in_ul:
        body.append("</ul>")
        in_ul = False


for line in md.split("\n"):
    ls = line.strip()
    if not ls:
        close_ul()
        continue
    if ls.startswith("# "):
        close_ul()
        title = ls[2:].strip()
        sl = slug(title)
        chapters.append((sl, title))
        body.append(f'\n<h1 class="chapter-title" id="{sl}">{inline(title)}</h1>')
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

toc = ['<nav class="toc">', "<h2>Contents</h2>", "<ul>"]
toc += [f'<li><a href="#{sl}">{inline(t)}</a></li>' for sl, t in chapters]
toc += ["</ul>", "</nav>"]

open("book.html", "w").write(shell + "\n".join(toc) + "\n" + "\n".join(body) + footer)
print("book.html:", len(chapters), "sections")
