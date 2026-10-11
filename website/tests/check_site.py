#!/usr/bin/env python3
"""Validate the deployable site, including project-subpath links and report anchors."""
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2] / "docs"
errors = []


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path, self.ids, self.links, self.headings = path, [], [], []
        self.current, self.main = 0, 0
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag in ("a", "link") and "href" in a:
            self.links.append(a["href"])
        if tag in ("script", "img") and "src" in a:
            self.links.append(a["src"])
        if tag == "img" and "alt" not in a:
            errors.append(f"{self.path.name}: image without alt text")
        if tag == "h1":
            self.headings.append(tag)
        if tag == "main":
            self.main += 1
        if a.get("aria-current") == "page":
            self.current += 1


documents = {path.resolve(): Document(path) for path in ROOT.glob("*.html")}
assert len(documents) == 6, "Expected all six site pages"
for path, document in documents.items():
    if len(document.headings) != 1 or document.main != 1 or document.current != 1:
        errors.append(f"{path.name}: expected one h1, main, and current navigation item")
    duplicates = [value for value, count in Counter(document.ids).items() if count > 1]
    if duplicates:
        errors.append(f"{path.name}: duplicate IDs: {duplicates}")
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
    if path.is_file():
        content = path.read_text()
        if re.search(r"file://|/Users/|/home/|localhost:|127\.0\.0\.1:", content):
            errors.append(f"{path.relative_to(ROOT)}: local-machine reference in website")
        if path.suffix == ".json":
            json.loads(content)

source = json.loads((ROOT.parent / "website/content.json").read_text())
assert len(source["publications"]) == 8
assert len(source["resources"]) == 7
assert sum(record["count"] for record in source["resources"]) == 109
assert len([anchor for anchor in documents[(ROOT / "strategy.html").resolve()].ids if re.match(r"\d+-", anchor)]) == 12
if errors:
    raise SystemExit("\n".join(errors))
print("PASS: six pages, internal links and fragments, page landmarks, portable assets, JSON, and collection counts")
