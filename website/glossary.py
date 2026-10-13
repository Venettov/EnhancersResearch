"""Shared bilingual glossary rendering and safe, build-time term annotation."""
import re
from html import escape
from html.parser import HTMLParser


LABELS = {
    "en": {
        "title": "Glossary", "description": "Plain-language explanations of the cells, DNA, experiments, and analysis behind this research.",
        "hint": "Biology in plain language", "help": "Terms with dotted underlines open explanations and sources.",
        "browse": "Browse the glossary", "meaning": "In plain language", "context": "Why it matters here", "sources": "Sources & further reading",
        "papers": "In our collected papers", "close": "Close explanation", "explain": "Explain", "entry": "Open this glossary entry",
        "search": "Find a term", "placeholder": "HepG2, enhancer, barcode…", "empty": "No terms match the current search and topic filters.",
        "clear": "Clear search", "all": "All topics", "topic": "Topic", "count": "terms", "read": "Plain-language definitions introduce the biology behind this research.",
        "intro": "We are reproducing an earlier enhancer prediction method, then testing how its predictions relate to activity measured in different cells. This glossary explains the biology, model inputs, and fair evaluation needed for that work. Each entry includes a meaning, a connection to this project, and places to read more.",
        "external": "Source material may use technical language. The explanations here are written for this project; linked papers and reference sites retain their original language.",
        "categories": {"basics": "DNA & gene regulation", "cells": "Cells & cell states", "experiments": "Experiments & resources", "analysis": "Reading the evidence", "models": "Computational models"},
    },
    "es": {
        "title": "Glosario", "description": "Explicaciones sencillas sobre las células, el ADN, los experimentos y los análisis de esta investigación.",
        "hint": "Biología en palabras sencillas", "help": "Los términos con subrayado de puntos abren explicaciones y fuentes.",
        "browse": "Explorar el glosario", "meaning": "En palabras sencillas", "context": "Por qué importa aquí", "sources": "Fuentes y lecturas para saber más",
        "papers": "En nuestros artículos recopilados", "close": "Cerrar explicación", "explain": "Explicar", "entry": "Abrir esta entrada del glosario",
        "search": "Buscar un término", "placeholder": "HepG2, potenciador, código de barras…", "empty": "No hay términos que coincidan con la búsqueda y los filtros de tema actuales.",
        "clear": "Borrar búsqueda", "all": "Todos los temas", "topic": "Tema", "count": "términos", "read": "Las definiciones en lenguaje sencillo presentan la biología de esta investigación.",
        "intro": "Estamos reproduciendo un método anterior de predicción de potenciadores y después evaluaremos su relación con actividad medida en células distintas. Este glosario explica la biología, las entradas del modelo y la evaluación rigurosa que requiere ese trabajo. Cada entrada incluye su significado, su relación con el proyecto y lecturas para saber más.",
        "external": "Las fuentes pueden usar lenguaje técnico. Estas explicaciones se han redactado para el proyecto; los artículos y sitios enlazados conservan su idioma original.",
        "categories": {"basics": "ADN y regulación génica", "cells": "Células y estados celulares", "experiments": "Experimentos y recursos", "analysis": "Interpretar la evidencia", "models": "Modelos computacionales"},
    },
}


def entries(data, language, publications):
    """Resolve references centrally, keeping citations identical in both languages."""
    result = []
    papers = {p["id"]: p for p in publications}
    for term in data["terms"]:
        item = {"id": term["id"], "category": term["category"], **term[language]}
        item["sources"] = [{"url": data["sources"][s]["url"], "label": data["sources"][s][language]} for s in term["sources"]]
        item["papers"] = [{"url": f'publications.html#{p}', "label": f'{p} · {papers[p]["title"]}'} for p in term["papers"]]
        result.append(item)
    return result


def references(items):
    return '<ul>' + ''.join(f'<li><a href="{escape(i["url"], quote=True)}">{escape(i["label"])}</a></li>' for i in items) + '</ul>'


def glossary_html(items, language):
    ui = LABELS[language]
    options = ''.join(f'<option value="{key}">{escape(label)}</option>' for key, label in ui["categories"].items())
    cards = []
    for item in sorted(items, key=lambda i: i["name"].casefold()):
        sources = (f'<h3>{ui["sources"]}</h3>{references(item["sources"])}' if item["sources"] else '')
        papers = (f'<h3>{ui["papers"]}</h3>{references(item["papers"])}' if item["papers"] else '')
        aliases = escape(' '.join(item["aliases"]), quote=True)
        cards.append(f'''<article class="glossary-card" id="term-{item['id']}" data-glossary-entry data-category="{item['category']}" data-aliases="{aliases}">
<p class="eyebrow">{ui['categories'][item['category']]}</p><h2 tabindex="-1">{escape(item['name'])}</h2><p>{escape(item['definition'])}</p><h3>{ui['context']}</h3><p>{escape(item['context'])}</p>{sources}{papers}</article>''')
    return f'''<section class="glossary-intro"><p class="lead">{ui['read']}</p><p>{ui['intro']}</p><p class="small-note">{ui['external']}</p></section>
<div class="glossary-tools" data-glossary-tools hidden><div><label for="glossary-search">{ui['search']}</label><input id="glossary-search" type="search" placeholder="{ui['placeholder']}" autocomplete="off"></div><div><label for="glossary-topic">{ui['topic']}</label><select id="glossary-topic"><option value="all">{ui['all']}</option>{options}</select></div><button type="button" data-glossary-clear>{ui['clear']}</button><p id="glossary-count" role="status" aria-live="polite"></p></div>
<p id="glossary-empty" hidden>{ui['empty']}</p><div class="glossary-grid">{''.join(cards)}</div>'''


def reader_help(language):
    ui = LABELS[language]
    return f'''<div class="reader-help"><div><strong>{ui['hint']}</strong><span>{ui['help']}</span></div><a href="glossary.html">{ui['browse']} <span aria-hidden="true">→</span></a></div>'''


def dialog_html(language):
    ui = LABELS[language]
    return f'''<dialog class="term-dialog" id="term-dialog" aria-labelledby="term-title" aria-describedby="term-definition"><div class="term-dialog-shell"><div class="term-dialog-top"><p class="eyebrow" id="term-category"></p><button type="button" data-term-close aria-label="{ui['close']}">×</button></div><h2 id="term-title" tabindex="-1"></h2><p class="term-definition" id="term-definition"></p><div class="term-project"><h3>{ui['context']}</h3><p id="term-context"></p></div><section id="term-sources"><h3>{ui['sources']}</h3><ul></ul></section><section id="term-papers"><h3>{ui['papers']}</h3><ul></ul></section><a class="term-entry-link" id="term-entry-link" href="glossary.html">{ui['entry']} →</a></div></dialog>'''


class Annotator(HTMLParser):
    """Match visible prose only, never attributes, source links, code, or controls."""
    excluded = {"a", "button", "script", "style", "code", "pre", "textarea", "select", "label", "summary", "nav", "svg", "h1", "h2", "h3", "h4"}
    void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, items, language):
        super().__init__(convert_charrefs=False)
        self.output, self.stack = [], []
        self.items = {alias.casefold(): item for item in items for alias in item["aliases"]}
        self.pattern = re.compile(r'(?<![\w])(?:' + '|'.join(re.escape(a) for a in sorted(self.items, key=len, reverse=True)) + r')(?![\w])', re.I)
        self.explain = LABELS[language]["explain"]

    def handle_starttag(self, tag, attrs):
        self.output.append(self.get_starttag_text())
        if tag not in self.void:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.output.append(f'</{tag}>')
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, value):
        if self.excluded.intersection(self.stack):
            self.output.append(value)
            return
        def wrap(match):
            item = self.items[match.group().casefold()]
            label = escape(f'{self.explain}: {match.group()}', quote=True)
            return f'<a class="term-link" href="glossary.html#term-{item["id"]}" data-term="{item["id"]}" aria-label="{label}">{escape(match.group())}</a>'
        self.output.append(self.pattern.sub(wrap, value))

    def handle_entityref(self, name):
        self.output.append(f'&{name};')

    def handle_charref(self, name):
        self.output.append(f'&#{name};')

    def handle_comment(self, data):
        self.output.append(f'<!--{data}-->')


def annotate(content, items, language):
    parser = Annotator(items, language)
    parser.feed(content)
    parser.close()
    return ''.join(parser.output)
