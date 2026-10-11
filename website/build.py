#!/usr/bin/env python3
"""Build the research website using only Python's standard library."""
import json
import re
import shutil
from html import escape, unescape
from pathlib import Path
from string import Template

SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parent / "docs"
PAGES = {
    "index": ("Home", "Enhancer biology, cellular context, and the experimental evidence behind a research project in regulatory genomics."),
    "research": ("Research", "Questions about enhancer activity, cellular context, assay reliability, and regulatory grammar."),
    "publications": ("Publications", "A curated reading collection of experimental studies, regulatory annotations, and sequence models."),
    "resources": ("Resources", "Seven complementary collections of experimental measurements, annotations, and prediction resources."),
    "notes": ("Research Notes", "Observations, decisions, and open questions as the enhancer research project develops."),
    "strategy": ("Evidence & Strategy", "Research report 01: enhancer biology, the collected literature, and an analysis-first research strategy."),
}


def publications_html(records):
    result = []
    for record in records:
        p = {key: escape(str(value), quote=True) for key, value in record.items() if key != "earlier"}
        earlier = record.get("earlier")
        version = (f'<a class="publication-earlier" href="{escape(earlier["url"], quote=True)}">'
                   f'{escape(earlier["label"])} ↗</a>') if earlier else ""
        result.append(f'''<article class="publication" id="{p['id']}" data-publication data-type="{p['type']}">
<div class="publication-year">{p['year']}<span class="publication-id">{p['id']}</span></div>
<div><p class="publication-authors">{p['authors']}</p><h2><a href="{p['url']}">{p['title']}</a></h2><p class="publication-journal">{p['journal']}</p><p class="publication-summary">{p['summary']}</p>{version}</div>
<div class="publication-note"><span class="tag">{p['label']}</span><p>{p['note']}</p><a href="{p['url']}">Read the source ↗</a></div></article>''')
    return "\n".join(result)


def resources_html(records):
    result = []
    for record in records:
        r = {key: escape(str(value), quote=True) for key, value in record.items()}
        guide = f"https://github.com/Venettov/EnhancersResearch/blob/main/NEW_2026_DATA/{r['folder']}/STUDY_GUIDE.md"
        result.append(f'''<details class="resource" id="collection-{r['number']}"><summary><span class="resource-number">{r['number']}</span><span class="resource-name">{r['title']}</span><span class="resource-kind">{r['kind']}</span><span class="resource-size">{r['count']} resources<br>{r['size']}</span></summary>
<div class="resource-body"><p>{r['description']}</p><div><h3>Research use</h3><p>{r['use']}</p></div><div><h3>Interpretation</h3><p>{r['limit']}</p></div><div class="resource-actions"><a href="{r['url']}">Original source ↗</a><a href="{guide}">Study guide on GitHub ↗</a></div></div></details>''')
    return "\n".join(result)


def intro_html(slug, title, description):
    if slug == "index":
        return '''<section class="hero" aria-labelledby="page-title"><div class="container hero-grid"><div class="hero-copy"><p class="eyebrow">Exploring the regulatory genome</p><h1 id="page-title">Understanding enhancers.<br>In context.</h1><p>From DNA sequence to cellular activity: a research project connecting functional experiments, regulatory maps, and careful computation.</p><a class="hero-link" href="research.html">Explore our research <span aria-hidden="true">→</span></a></div><img class="hero-art" src="assets/context.svg" alt="Conceptual illustration connecting one DNA sequence to HepG2, K562, and WTC11 cells; not measured data." width="520" height="342"></div></section>'''
    kicker = "Research report 01 · 10 October 2026" if slug == "strategy" else "EnhancersResearch / " + title
    return f'''<section class="page-intro" aria-labelledby="page-title"><div class="container"><p class="eyebrow">{escape(kicker)}</p><h1 id="page-title">{escape(title)}</h1><p>{escape(description)}</p></div></section>'''


def build():
    data = json.loads((SOURCE / "content.json").read_text())
    template = Template((SOURCE / "template.html").read_text())
    OUTPUT.mkdir(exist_ok=True)
    for directory in ("assets", "data"):
        shutil.copytree(SOURCE / directory, OUTPUT / directory, dirs_exist_ok=True)
    for slug, (title, description) in PAGES.items():
        content = (SOURCE / "pages" / f"{slug}.html").read_text()
        if slug == "publications":
            content = Template(content).substitute(publications=publications_html(data["publications"]))
        elif slug == "resources":
            content = Template(content).substitute(resources=resources_html(data["resources"]))
        elif slug == "strategy":
            headings = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', content, re.S)
            toc = ''.join(f'<li><a href="#{escape(anchor, quote=True)}">{escape(unescape(re.sub("<[^>]+>", "", label)))}</a></li>' for anchor, label in headings)
            notice = '<div class="report-notice"><strong>Foundational report · 10 October 2026.</strong> This reading edition preserves the original research strategy. Later QC observations and unresolved reproduction details are recorded in the <a href="notes.html#qc">research notes</a>.</div>'
            content = f'<div class="report-layout"><article class="report-body">{notice}{content}</article><aside class="report-toc" aria-label="Report contents"><h2>In this report</h2><ol>{toc}</ol><a class="text-link" href="#main">Back to the beginning ↑</a></aside></div>'
        nav = ''.join(f'<a href="{name}.html"' + (' aria-current="page"' if name == slug else '') + f'>{escape(label)}</a>' for name, (label, _) in PAGES.items() if name != "strategy")
        rendered = template.substitute(base="", title=escape(title), description=escape(description, quote=True), body_class=f"page-{slug}", navigation=nav, intro=intro_html(slug, title, description), content=content)
        if slug == "strategy":
            rendered = rendered.replace('class="nav-report"', 'class="nav-report" aria-current="page"')
        (OUTPUT / f"{slug}.html").write_text(rendered, encoding="utf-8")
    (OUTPUT / ".nojekyll").write_text("")
    print(f"Built {len(PAGES)} pages in {OUTPUT}")


if __name__ == "__main__":
    build()
