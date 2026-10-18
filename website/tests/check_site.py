#!/usr/bin/env python3
"""Validate the deployable site, including project-subpath links and report anchors."""
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2] / "docs"
sys.path.insert(0, str(ROOT.parent / "website"))
from glossary import LABELS, annotate, entries
errors = []


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path, self.ids, self.links, self.headings = path, [], [], []
        self.current, self.main = 0, 0
        self.language, self.language_links = None, {}
        self.tags, self.text = Counter(), []
        self.term_links = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-term" in a:
            self.term_links.append(a)
        self.tags[tag] += 1
        if tag == "html":
            self.language = a.get("lang")
        if "data-language" in a:
            self.language_links[a["data-language"]] = a.get("href")
        if "id" in a:
            self.ids.append(a["id"])
        if tag in ("a", "link") and "href" in a:
            self.links.append(a["href"])
        if tag in ("script", "img", "video", "source") and "src" in a:
            self.links.append(a["src"])
        if tag == "video" and "poster" in a:
            self.links.append(a["poster"])
        if "data-animation-src" in a:
            self.links.append(a["data-animation-src"])
        if tag == "img" and "alt" not in a:
            errors.append(f"{self.path.name}: image without alt text")
        if tag == "h1":
            self.headings.append(tag)
        if tag == "main":
            self.main += 1
        if a.get("aria-current") == "page":
            self.current += 1

    def handle_data(self, text):
        self.text.append(text)


documents = {path.resolve(): Document(path) for path in ROOT.rglob("*.html")}
assert len(documents) == 20, "Expected ten pages in both languages"
for path, document in documents.items():
    if len(document.headings) != 1 or document.main != 1 or document.current != 1:
        errors.append(f"{path.name}: expected one h1, main, and current navigation item")
    duplicates = [value for value, count in Counter(document.ids).items() if count > 1]
    if duplicates:
        errors.append(f"{path.name}: duplicate IDs: {duplicates}")
    expected_language = "es" if path.parent.name == "es" else "en"
    if document.language != expected_language or set(document.language_links) != {"en", "es"}:
        errors.append(f"{path}: incorrect language metadata or missing language switch")
    for language, href in document.language_links.items():
        linked_page = documents.get((path.parent / href).resolve())
        if not linked_page or linked_page.language != language or linked_page.path.name != path.name:
            errors.append(f"{path}: language switch does not lead to its translated counterpart")
    for href in document.links:
        target = urlsplit(href)
        if target.scheme in ("https", "http", "mailto"):
            continue
        if target.scheme or target.netloc or target.path.startswith("/"):
            errors.append(f"{path.name}: nonportable URL {href}")
            continue
        resolved = (path.parent / unquote(target.path)).resolve() if target.path else path
        if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
            errors.append(f"{path.name}: missing or out-of-site target {href}")
        elif target.fragment and resolved in documents and unquote(target.fragment) not in documents[resolved].ids:
            errors.append(f"{path.name}: missing anchor {href}")

for path in ROOT.rglob("*"):
    if path.is_file() and path.name != ".DS_Store":
        # Media assets do not contain website text or portable links.
        if path.suffix.lower() in {".gif", ".jpg", ".mp4"}:
            continue
        content = path.read_text()
        if re.search(r"file://|/Users/|/home/|localhost:|127\.0\.0\.1:", content):
            errors.append(f"{path.relative_to(ROOT)}: local-machine reference in website")
        if path.suffix == ".json":
            json.loads(content)

source = json.loads((ROOT.parent / "website/content.json").read_text())
assert len(source["publications"]) == 12
assert {item["id"] for item in source["publications"] if item["id"].startswith("L")} == {"L01", "L02", "L03", "L04"}
assert len(source["resources"]) == 7
assert sum(record["count"] for record in source["resources"]) == 109
glossary = json.loads((ROOT.parent / "website/glossary.json").read_text())
term_ids = {term["id"] for term in glossary["terms"]}
assert len(term_ids) == len(glossary["terms"]) == 64
for term in glossary["terms"]:
    assert re.fullmatch(r"[a-z0-9-]+", term["id"])
    assert term["sources"] or term["papers"], f"No sources for {term['id']}"
    assert all(key in glossary["sources"] for key in term["sources"])
    assert all(p in {item["id"] for item in source["publications"]} for p in term["papers"])
    for language in ("en", "es"):
        assert term["category"] in LABELS[language]["categories"]
        assert all(term[language].get(key) for key in ("name", "definition", "context", "aliases"))
for language in ("en", "es"):
    aliases = {}
    for term in glossary["terms"]:
        for alias in term[language]["aliases"]:
            previous = aliases.setdefault(alias.casefold(), term["id"])
            assert previous == term["id"], f"Ambiguous alias: {alias}"
    localized = entries(glossary, language, source["publications"])
    # Annotation must preserve wording, entities, controls, links and code.
    untouched = '<a href="https://example.com/HepG2">HepG2 DNA</a><code>MPRA</code><button>K562</button><summary>WTC11</summary><h2>HepG2</h2>'
    assert annotate(untouched, localized, language) == untouched
    sample = '<p title="HepG2">HepG2 &amp; K562, WTC11. lentiMPRA; MPRA; notMPRA; DNABERT-Enhancer.</p>'
    annotated = annotate(sample, localized, language)
    assert annotated.count('data-term=') == 6
    assert 'data-term="lentimpra"' in annotated and 'data-term="dnabert"' in annotated
    assert re.sub(r'<a class="term-link"[^>]+>(.*?)</a>', r'\1', annotated) == sample
for document in documents.values():
    for link in document.term_links:
        assert link["data-term"] in term_ids
        assert link["href"] == f'glossary.html#term-{link["data-term"]}'
        assert link.get("aria-label")
    if document.path.stem != "glossary":
        assert document.term_links, f"No explanations in {document.path}"
    else:
        assert {f"term-{term}" for term in term_ids} <= set(document.ids)
for path in ROOT.glob("*.html"):
    english = documents[path.resolve()]
    spanish = documents[(ROOT / "es" / path.name).resolve()]
    assert set(english.ids) == set(spanish.ids), f"Translation lost anchors in {path.name}"
    assert Counter(link for link in english.links if link.startswith("https://")) == Counter(link for link in spanish.links if link.startswith("https://")), f"Translation changed source citations in {path.name}"

for language_path in (ROOT, ROOT / "es"):
    report = documents[(language_path / "strategy.html").resolve()]
    assert len([anchor for anchor in report.ids if re.match(r"\d+-", anchor)]) == 12

# Check the full report's source structure and numerical facts, independently
# of the localized navigation and generated table of contents.
english_report = Document(ROOT.parent / "website/pages/strategy.html")
spanish_report = Document(ROOT.parent / "website/i18n/es/pages/strategy.html")
for tag in ("h2", "h3", "p", "table", "tr", "th", "td", "li", "article", "blockquote"):
    assert english_report.tags[tag] == spanish_report.tags[tag], f"Report translation lost {tag} content"
numbers = lambda doc: Counter(re.findall(r"\d+(?:[.,]\d+)*", " ".join(doc.text)))
assert numbers(english_report) == numbers(spanish_report), "Report numerical facts differ between languages"
if errors:
    raise SystemExit("\n".join(errors))
print("PASS: 20 localized pages; 12 publications; 64 sourced bilingual explanations; safe annotation; links, fragments, language switches, collections, and report structure/numerical parity")
