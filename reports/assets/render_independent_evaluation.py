#!/usr/bin/env python3
"""Render report 04's limited Markdown syntax without external dependencies."""
import html
from pathlib import Path
import re

REPORTS = Path(__file__).resolve().parents[1]
SOURCE = REPORTS / '04_ienhancer_2l_independent_evaluation.md'
OUTPUT = SOURCE.with_suffix('.html')


def inline(text):
    text = html.escape(text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  lambda m: '<a href="' + html.escape(html.unescape(m[2]), quote=True) + '">' + m[1] + '</a>', text)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def main():
    body, contents = [], []
    list_kind = None
    paragraph = []

    def flush():
        if paragraph:
            body.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    def end_list():
        nonlocal list_kind
        if list_kind:
            body.append(f'</{list_kind}>')
            list_kind = None

    for line in SOURCE.read_text().splitlines():
        if not line.strip():
            flush()
            end_list()
        elif line.startswith('# '):
            flush(); end_list()
            body.append('<h1>' + inline(line[2:]) + '</h1>')
        elif line.startswith('## '):
            flush(); end_list()
            title = line[3:]
            anchor = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            contents.append(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>')
            body.append(f'<h2 id="{anchor}">' + inline(title) + '</h2>')
        elif re.match(r'\d+\. ', line):
            flush()
            if list_kind != 'ol':
                end_list(); body.append('<ol>'); list_kind = 'ol'
            body.append('<li>' + inline(re.sub(r'^\d+\. ', '', line)) + '</li>')
        else:
            end_list()
            paragraph.append(line)
    flush(); end_list()
    toc = '<details class="contents"><summary>Contents</summary><ol>' + ''.join(contents) + '</ol></details>'
    body.insert(3, toc)
    OUTPUT.write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Independent evaluation of the iEnhancer-2L reconstruction</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f7f4;color:#21383c;font:16px/1.75 system-ui,-apple-system,sans-serif}main{max-width:1000px;margin:28px auto 70px;padding:36px 52px;background:white;border:1px solid #d8e1dd;border-top:5px solid #27666a;border-radius:6px}.local{font-size:12px;letter-spacing:.08em;font-weight:650;color:#27666a}h1,h2{line-height:1.2;font-family:Georgia,serif;font-weight:500}h1{font-size:38px;margin:16px 0 25px}h2{font-size:27px;margin:40px 0 16px;padding-top:20px;border-top:1px solid #d8e1dd;scroll-margin-top:24px}p{margin:16px 0}a{color:#236366;text-underline-offset:3px;overflow-wrap:anywhere}li{padding-left:4px;margin:12px 0}a:focus-visible,summary:focus-visible{outline:3px solid #b47332;outline-offset:4px}.contents{padding:12px 18px;background:#eef4f0;border:1px solid #d8e1dd;margin:24px 0}.contents summary{cursor:pointer;font-weight:650}.contents ol{columns:2;font-size:14px}.contents li{break-inside:avoid;margin:5px 0}main>p:first-of-type{padding:14px 18px;background:#eef4f0;border-left:3px solid #27666a;font-size:14px}@media(max-width:650px){main{padding:24px 20px;margin:0;border-radius:0}h1{font-size:30px}.contents ol{columns:1}}@media print{body{background:white}main{border:0;margin:0;padding:0}.local,.contents{display:none}h2{break-after:avoid}a{color:inherit}}
</style></head><body><main><div class="local">LOCAL RESEARCH PROTOCOL · NOT PUBLISHED</div>''' + '\n'.join(body) + '</main></body></html>\n')
    print(f'Rendered {OUTPUT.name}')


if __name__ == '__main__':
    main()
