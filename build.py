#!/usr/bin/env python3
"""indexhibit — monochrome static builder.

Reads src/posts/*.md, src/zettels/*.md, src/about.md (+ entries.json, style.css,
src/media/) and writes a complete HTML site to docs/.

Only JavaScript on the site is KaTeX (CDN, deferred) for $...$ / $$...$$ math.
"""

import json
import re
import shutil
import sys
import time
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
POSTS_SRC = SRC / "posts"
ZETTELS_SRC = SRC / "zettels"
MEDIA_SRC = SRC / "media"
OUT = ROOT / "docs"

KATEX_CSS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" crossorigin="anonymous">'
KATEX_JS = '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>'
KATEX_AUTO = '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" crossorigin="anonymous" onload="renderMathInElement(document.body, {delimiters: [{left: \'$$\', right: \'$$\', display: true}, {left: \'$\', right: \'$\', display: false}]});"></script>'

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKI_RE = re.compile(r"\[\[([a-z0-9][a-z0-9-]*)\]\]")


def parse_file(path: Path):
    """Return (meta, body) or None if unparsable."""
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    return meta, text[m.end():]


def load_entries():
    with open(ROOT / "entries.json", encoding="utf-8") as f:
        return json.load(f)


class Site:
    def __init__(self):
        self.posts = {}   # slug -> {meta, body}
        self.zettels = {} # slug -> {meta, body}
        self.links = {}   # slug -> set(target slugs) actually outgoing per page
        self.backlinks = {}  # slug -> set(source slugs)

    def load(self):
        for d, store in ((POSTS_SRC, self.posts), (ZETTELS_SRC, self.zettels)):
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.md")):
                if p.name.startswith("_"):
                    continue
                parsed = parse_file(p)
                if parsed is None:
                    print(f"  ! skipping {p.name}: no/invalid frontmatter")
                    continue
                meta, body = parsed
                store[p.stem] = {"meta": meta, "body": body}
        # wiki-link graph (posts + zettels)
        for slug, item in {**self.posts, **self.zettels}.items():
            targets = set(WIKI_RE.findall(item["body"]))
            self.links[slug] = targets
            for t in targets:
                self.backlinks.setdefault(t, set()).add(slug)

    def slug_exists(self, slug):
        return slug in self.posts or slug in self.zettels

    def slug_href(self, slug):
        if slug in self.posts:
            return f"posts/{slug}.html"
        if slug in self.zettels:
            return f"zettels/{slug}.html"
        return None

    def wiki_links_html(self, body, depth_prefix=""):
        def repl(m):
            slug = m.group(1)
            href = self.slug_href(slug)
            if href:
                title = self.posts.get(slug, self.zettels.get(slug, {}))["meta"].get("title", slug)
                return f'<a href="{depth_prefix}{href}">{title}</a>'
            return f'<span class="wiki-broken">{slug}</span>'
        return WIKI_RE.sub(repl, body)


MATH_TOKEN_RE = re.compile(r"§§MATH(\d+)§§")


def md_to_html(body: str):
    """Markdown → HTML with math protected from mangling (KaTeX renders client-side)."""
    stash = []

    def protect(m):
        stash.append(m.group(0))
        return f"§§MATH{len(stash) - 1}§§"

    protected = re.sub(r"\$\$.*?\$\$|\$[^$\n]+\$", protect, body, flags=re.DOTALL)
    html = markdown.markdown(protected, extensions=["tables", "fenced_code"])
    return MATH_TOKEN_RE.sub(lambda m: stash[int(m.group(1))], html)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    site = Site()
    site.load()
    cfg = load_entries()

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    (OUT / "zettels").mkdir(parents=True)
    if MEDIA_SRC.is_dir():
        shutil.copytree(MEDIA_SRC, OUT / "media")

    for slug, item in sorted(site.posts.items()):
        write_post(site, cfg, slug, item)
    for slug, item in sorted(site.zettels.items()):
        write_zettel(site, cfg, slug, item)
    write_about(site, cfg)
    write_index(site, cfg)
    shutil.copy(ROOT / "style.css", OUT / "style.css")

    drafts = [s for s, i in site.posts.items() if i["meta"].get("draft")]
    print(f"  posts: {len(site.posts)} ({len(drafts)} draft)  zettels: {len(site.zettels)}  out: {OUT}")


def media_html(meta, prefix):
    files = meta.get("images") or []
    return "".join(f'<img src="{prefix}media/{f}" alt="{esc(f.rsplit(".", 1)[0])}" loading="lazy">\n' for f in files)


def page(cfg, title, body_html, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — {esc(cfg['title'])}</title>
<link rel="stylesheet" href="style.css">
{KATEX_CSS}
{KATEX_JS}
{KATEX_AUTO}
{extra_head}
</head>
<body>
<header class="site-head">
<p class="site-title"><a href="{STYLE_PREFIX}index.html">{esc(cfg['title'])}</a></p>
<p class="site-sub">{esc(cfg.get('subtitle', ''))}</p>
</header>
<main>
{body_html}
</main>
<footer class="site-foot">
<p>{esc(cfg['author'])} · <a href="mailto:{esc(cfg['contact'])}">{esc(cfg['contact'])}</a></p>
<p class="dim">{esc(cfg['base_url'])}</p>
</footer>
</body>
</html>"""


# prefix for links from pages nested one level deep (posts/, zettels/)
STYLE_PREFIX = ""


def nested_page(cfg, title, body_html):
    global STYLE_PREFIX
    STYLE_PREFIX = "../"
    html = page(cfg, title, body_html)
    html = html.replace('href="style.css"', 'href="../style.css"').replace('href="index.html"', 'href="../index.html"')
    STYLE_PREFIX = ""
    return html


def write_post(site, cfg, slug, item):
    meta, body = item["meta"], item["body"]
    title = meta.get("title", slug)
    date = meta.get("date", "")
    ptype = meta.get("type", "note")
    klass = "post draft" if meta.get("draft") else "post"
    parts = [f'<article class="{klass} type-{esc(ptype)}">']
    parts.append(f'<h1>{esc(title)}</h1>')
    parts.append(f'<p class="meta">{esc(date)} · {esc(ptype)}</p>')
    parts.append(media_html(meta, "../"))
    parts.append(site.wiki_links_html(md_to_html(body), "../"))
    parts.append("</article>")
    nav = ['<nav class="pager">', f'<a href="../index.html">index</a>', "</nav>"]
    (OUT / "posts" / f"{slug}.html").write_text(nested_page(cfg, title, "\n".join(parts + nav)), encoding="utf-8")


def write_zettel(site, cfg, slug, item):
    meta, body = item["meta"], item["body"]
    title = meta.get("title", slug)
    date = meta.get("date", "")
    parts = [f'<article class="zettel">']
    parts.append(f'<h1>{esc(title)}</h1>')
    parts.append(f'<p class="meta">{esc(date)} · zettel</p>')
    parts.append(site.wiki_links_html(md_to_html(body), "../"))

    outgoing = sorted(t for t in site.links.get(slug, ()) if site.slug_exists(t))
    if outgoing:
        parts.append('<section class="linksec"><h2>Links to</h2><ul>')
        for t in outgoing:
            href = site.slug_href(t)
            ttitle = site.posts.get(t, site.zettels.get(t, {}))["meta"].get("title", t)
            parts.append(f'<li><a href="../{href}">{esc(ttitle)}</a></li>')
        parts.append("</ul></section>")
    incoming = sorted(site.backlinks.get(slug, ()))
    if incoming:
        parts.append('<section class="linksec"><h2>Linked from</h2><ul>')
        for s in incoming:
            href = site.slug_href(s)
            stitle = site.posts.get(s, site.zettels.get(s, {}))["meta"].get("title", s)
            parts.append(f'<li><a href="../{href}">{esc(stitle)}</a></li>')
        parts.append("</ul></section>")
    parts.append("</article>")
    nav = ['<nav class="pager">', '<a href="../index.html">index</a>', "</nav>"]
    (OUT / "zettels" / f"{slug}.html").write_text(nested_page(cfg, title, "\n".join(parts + nav)), encoding="utf-8")


def write_about(site, cfg):
    parsed = parse_file(SRC / "about.md")
    body = parsed[1] if parsed else "(no about)"
    parts = ['<article class="about">', "<h1>About</h1>", site.wiki_links_html(md_to_html(body)), "</article>"]
    (OUT / "about.html").write_text(page(cfg, "About", "\n".join(parts)), encoding="utf-8")


def write_index(site, cfg):
    parts = []
    groups = [("exhibit", "Exhibits"), ("note", "Notes"), ("log", "Logs")]
    for gtype, label in groups:
        items = [(s, i) for s, i in site.posts.items() if i["meta"].get("type") == gtype]
        items.sort(key=lambda si: str(si[1]["meta"].get("date", "")), reverse=True)
        if not items:
            continue
        parts.append(f'<section class="index-group"><h2>{label}</h2><ul>')
        for s, i in items:
            m = i["meta"]
            date = str(m.get("date", ""))
            date = date[:10] if len(date) >= 10 else date
            draft = ' <span class="draftflag">draft</span>' if m.get("draft") else ""
            parts.append(f'<li><a href="posts/{s}.html">{esc(m.get("title", s))}</a>'
                         f'<span class="meta">{esc(date)}{draft}</span></li>')
        parts.append("</ul></section>")
    other = [(s, i) for s, i in site.posts.items() if i["meta"].get("type") not in ("exhibit", "note", "log")]
    if other:
        parts.append('<section class="index-group"><h2>Other</h2><ul>')
        for s, i in sorted(other):
            parts.append(f'<li><a href="posts/{s}.html">{esc(i["meta"].get("title", s))}</a></li>')
        parts.append("</ul></section>")
    if site.zettels:
        parts.append(f'<p class="dim index-zettels">{len(site.zettels)} zettels in the note graph.</p>')
    parts.append('<nav class="pager"><a href="about.html">about</a></nav>')
    (OUT / "index.html").write_text(page(cfg, cfg.get("subtitle", "index"), "\n".join(parts)), encoding="utf-8")


def watch():
    print("watching src/ entries.json style.css — Ctrl-C to stop")
    watched = [POSTS_SRC, ZETTELS_SRC, MEDIA_SRC, ROOT / "entries.json", ROOT / "style.css"]
    last = {}
    while True:
        stamp = {}
        for w in watched:
            if w.is_dir():
                for p in w.rglob("*"):
                    if p.is_file():
                        stamp[p] = p.stat().st_mtime
            elif w.is_file():
                stamp[w] = w.stat().st_mtime
        if stamp != last and last:
            print("change detected — rebuilding")
            try:
                build()
            except Exception as e:
                print(f"  ! build error: {e}")
        last = stamp
        time.sleep(1)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        build()
