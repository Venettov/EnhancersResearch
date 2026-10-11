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
def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def localized_data(language):
    data = read_json(SOURCE / "content.json")
    if language == "en":
        return data
    translations = read_json(SOURCE / "i18n" / language / "content.json")
    for collection, key, required in (
        ("publications", "id", {"label", "title", "summary", "note"}),
        ("resources", "number", {"title", "kind", "description", "use", "limit"}),
    ):
        overrides = {item[key]: item for item in translations[collection]}
        assert set(overrides) == {item[key] for item in data[collection]}, "Incomplete translated collection"
        for item in data[collection]:
            translated = overrides[item[key]]
            assert required <= translated.keys(), f"Missing translations for {item[key]}"
            if "earlier" in item:
                item["earlier"]["label"] = translated.pop("earlier_label")
            item.update(translated)
    return data


def publications_html(records, ui):
    result = []
    for record in records:
        p = {key: escape(str(value), quote=True) for key, value in record.items() if key != "earlier"}
        earlier = record.get("earlier")
        version = (f'<a class="publication-earlier" href="{escape(earlier["url"], quote=True)}">'
                   f'{escape(earlier["label"])} ↗</a>') if earlier else ""
        result.append(f'''<article class="publication" id="{p['id']}" data-publication data-type="{p['type']}">
<div class="publication-year">{p['year']}<span class="publication-id">{p['id']}</span></div>
<div><p class="publication-authors">{p['authors']}</p><h2><a href="{p['url']}">{p['title']}</a></h2><p class="publication-journal">{p['journal']}</p><p class="publication-summary">{p['summary']}</p>{version}</div>
<div class="publication-note"><span class="tag">{p['label']}</span><p>{p['note']}</p><a href="{p['url']}">{ui["read_source"]} ↗</a></div></article>''')
    return "\n".join(result)


def resources_html(records, ui):
    result = []
    for record in records:
        r = {key: escape(str(value), quote=True) for key, value in record.items()}
        guide = f"https://github.com/Venettov/EnhancersResearch/blob/main/NEW_2026_DATA/{r['folder']}/STUDY_GUIDE.md"
        result.append(f'''<details class="resource" id="collection-{r['number']}"><summary><span class="resource-number">{r['number']}</span><span class="resource-name">{r['title']}</span><span class="resource-kind">{r['kind']}</span><span class="resource-size">{r['count']} {ui['resources_label']}<br>{r['size']}</span></summary>
<div class="resource-body"><p>{r['description']}</p><div><h3>{ui["research_use"]}</h3><p>{r['use']}</p></div><div><h3>{ui["interpretation"]}</h3><p>{r['limit']}</p></div><div class="resource-actions"><a href="{r['url']}">{ui["original_source"]} ↗</a><a href="{guide}">{ui["study_guide"]} ↗</a></div></div></details>''')
    return "\n".join(result)


def intro_html(slug, title, description, ui, language, asset_base):
    if slug == "index":
        illustration = "context-es.svg" if language == "es" else "context.svg"
        return f'''<section class="hero" aria-labelledby="page-title"><div class="container hero-grid"><div class="hero-copy"><p class="eyebrow">{ui['hero_eyebrow']}</p><h1 id="page-title">{ui['hero_title']}</h1><p>{ui['hero_description']}</p><a class="hero-link" href="research.html">{ui['hero_link']} <span aria-hidden="true">→</span></a></div><img class="hero-art" src="{asset_base}assets/{illustration}" alt="{escape(ui['hero_alt'], quote=True)}" width="520" height="342"></div></section>'''
    kicker = ui["report_kicker"] if slug == "strategy" else "EnhancersResearch / " + title
    return f'''<section class="page-intro" aria-labelledby="page-title"><div class="container"><p class="eyebrow">{escape(kicker)}</p><h1 id="page-title">{escape(title)}</h1><p>{escape(description)}</p></div></section>'''


def language_switch(language, english_url, spanish_url, ui):
    links = []
    for code, label, url in (("en", "English", english_url), ("es", "Español", spanish_url)):
        current = ' aria-current="true"' if code == language else ''
        links.append(f'<a href="{url}" lang="{code}" hreflang="{code}" data-language="{code}"{current}>{label}</a>')
    return f'''<nav class="language-switch" aria-label="{ui['language_label']}"><svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></svg>{''.join(links)}</nav>'''


def build():
    template = Template((SOURCE / "template.html").read_text())
    OUTPUT.mkdir(exist_ok=True)
    for directory in ("assets", "data"):
        shutil.copytree(SOURCE / directory, OUTPUT / directory, dirs_exist_ok=True)
    english_ui = read_json(SOURCE / "i18n/en.json")
    for language in ("en", "es"):
        ui = english_ui if language == "en" else read_json(SOURCE / f"i18n/{language}/ui.json")
        assert ui.keys() == english_ui.keys(), "Incomplete interface translation"
        assert ui["pages"].keys() == english_ui["pages"].keys(), "Incomplete page metadata translation"
        data = localized_data(language)
        asset_base = "" if language == "en" else "../"
        page_source = SOURCE / "pages" if language == "en" else SOURCE / f"i18n/{language}/pages"
        destination = OUTPUT if language == "en" else OUTPUT / language
        destination.mkdir(exist_ok=True)
        for slug, (title, description) in ui["pages"].items():
            content = (page_source / f"{slug}.html").read_text()
            if slug == "publications":
                content = Template(content).substitute(publications=publications_html(data["publications"], ui))
            elif slug == "resources":
                content = Template(content).substitute(resources=resources_html(data["resources"], ui))
            elif slug == "strategy":
                headings = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', content, re.S)
                toc = ''.join(f'<li><a href="#{escape(anchor, quote=True)}">{escape(unescape(re.sub("<[^>]+>", "", label)))}</a></li>' for anchor, label in headings)
                notice = f'<div class="report-notice">{ui["report_notice"]}</div>'
                content = f'<div class="report-layout"><article class="report-body">{notice}{content}</article><aside class="report-toc" aria-label="{ui["report_contents"]}"><h2>{ui["in_report"]}</h2><ol>{toc}</ol><a class="text-link" href="#main">{ui["back_top"]} ↑</a></aside></div>'
            if language != "en":
                content = content.replace('href="data/', 'href="../data/')
            nav = ''.join(f'<a href="{name}.html"' + (' aria-current="page"' if name == slug else '') + f'>{escape(label)}</a>' for name, (label, _) in ui["pages"].items() if name != "strategy")
            english_url = f"{asset_base}{slug}.html"
            spanish_url = f"es/{slug}.html" if language == "en" else f"{slug}.html"
            rendered = template.substitute(**ui, language=language, asset_base=asset_base, english_url=english_url, spanish_url=spanish_url, language_switch=language_switch(language, english_url, spanish_url, ui), title=escape(title), description=escape(description, quote=True), body_class=f"page-{slug}", navigation=nav, intro=intro_html(slug, title, description, ui, language, asset_base), content=content)
            if slug == "strategy":
                rendered = rendered.replace('class="nav-report"', 'class="nav-report" aria-current="page"')
            (destination / f"{slug}.html").write_text(rendered, encoding="utf-8")
    (OUTPUT / ".nojekyll").write_text("")
    print(f"Built 12 pages in {OUTPUT} (English and Spanish)")


if __name__ == "__main__":
    build()
