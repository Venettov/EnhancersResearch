# EnhancersResearch website

A static research website inspired by the academic navigation and main-column/sidebar structure of the [MLBC Lab website](https://mlbclab.camden.rutgers.edu/), with the project's own typography, colors, illustration, and research content. It does not imply Rutgers affiliation.

## Build and preview

Requires Python 3.9 or later; no production dependencies, API keys, external fonts, analytics, or remote scripts.

```sh
python3 website/build.py
python3 website/tests/check_site.py
python3 -m http.server 8766 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8766`. Stop the server with Ctrl-C. All page and asset links work under a GitHub Pages project path such as `/EnhancersResearch/`.

## Edit content

- `template.html`: shared page shell, navigation, and footer.
- `pages/`: page copy. `strategy.html` is a reading edition adapted from `reports/01_enhancers_evidence_and_strategy.html` (10 October 2026); its source text is preserved except for portable source links and the web-edition footer. Edit this self-contained copy when updating the site.
- `content.json`: the eight publication records and seven resource collections. Journal versions and earlier preprints are grouped as one work.
- `i18n/en.json`: shared English interface text and page metadata.
- `i18n/es/`: complete Spanish page copy, including the full report, interface strings, and publication/resource translations. Identifiers, file names, numerical values, and source links retain their original meaning. External publications and machine-readable audit files remain original research sources.
- `assets/`: styles, progressive-enhancement JavaScript, and original SVG illustrations.
- The home page starts with a bilingual enhancer definition and a three-step SVG diagram in `pages/index.html` and `i18n/es/pages/index.html`. The original diagrams explain activators, Mediator, RNA polymerase II, and possible enhancer positions before, within, or after a gene. Wikipedia is linked as an overview alongside the primary studies supporting the explanation; visible labels and accessible SVG titles are localized. The panels stack on mobile, remain readable without JavaScript, and link to NLM and NHGRI sources. They are conceptual illustrations, not experimental measurements.
- `glossary.json`: 59 English/Spanish explanations, matching phrases, topic groups, and references. Each entry has a plain-language definition and project-specific context; collected-paper IDs resolve to the existing publication cards in the selected language.
- `glossary.py`: localized glossary interface, static glossary pages, popup shell, and build-time term annotation. Annotation preserves prose and avoids existing links, headings, code, and controls. Edit the source glossary, then rebuild; do not hand-edit generated term links.
- `assets/dna-helix-loop.gif`: a custom 640×360, 20 fps, four-second GIF made from the first five seconds of the supplied video. A one-second smooth dissolve joins the end back to the beginning while preserving forward motion; there is no held endpoint or hard cut. A shared palette limits color flicker. CSS masks fade all four edges and corners into the page background. `assets/dna-helix-loop-poster.jpg` is the matching still frame. The site loads the GIF only when visible and motion is allowed; pause, reduced motion, hidden tabs, and no JavaScript show the still instead. The original five-second clip remains in `assets/dna-helix.mp4` as the authoring source.
- `tools/make_hero_gif.py` and `tools/extract_hero_frames.swift`: optional media-authoring tools. On macOS with Swift and Pillow, run `python3 website/tools/make_hero_gif.py website/assets/dna-helix.mp4` to recreate the GIF and poster, then rebuild the site. These tools and dependencies are not used by the ordinary website build.
- `data/`: small provenance snapshots from the research workspace. `workspace_audit.json` is the full 12 October 2026 recheck, matching all non-metadata results of the 11 October audit. It preserves the distinctions between reference checksums, accepted-publication receipts, and recorded-size checks; the older download audit remains a separately dated record. Absolute local-machine paths have been removed. These are dated snapshots, not a live audit.
- `../docs/`: generated, deployable output. Rebuild and commit it alongside source changes. Do not edit generated pages directly.

The foundational report retains its original date and scope. Later QC observations live in Research Notes. Local findings are not presented as new biological results. Dataset counts include publications, supplements, code, and model archives. Large datasets, downloaded PDFs, and model weights are excluded from the website; links lead to source publications and study guides.

The English/Spanish switch occupies the top-left utility bar and links to the same page in the other language. Spanish pages live under `docs/es/`; navigation stays in the chosen language. JavaScript preserves section anchors when switching, without redirecting shared URLs or requiring cookies. Both languages remain fully readable and switchable without JavaScript; JavaScript also adds the compact mobile menu and localized publication search/filtering. Resource sections use native HTML disclosure controls. The layout includes keyboard focus styles, a skip link, reduced-motion support, and print styles.

Dotted-underlined terms throughout the original six pages open a native modal dialog with a definition, its relevance to the project, and supporting links. Escape, the close button, or the backdrop dismiss it; focus returns to the selected term without moving the reading position. The complete glossary is a seventh page in each language, with accent-insensitive search and topic filtering. Static term links reach the corresponding glossary entry when JavaScript or modal support is unavailable, and modified clicks retain normal link behavior. Definitions are bundled locally; no external lookup service is needed. External reference pages and papers retain their original language.

External source links open in a new tab, including references generated inside glossary popups. Internal navigation, language changes, and links to collected-paper cards stay in the current tab. External links include `noopener noreferrer` and a localized screen-reader description of the new-tab behavior; static links also work without JavaScript.

## Checks

`site-checks.yml` rebuilds and validates all fourteen pages, every local link/fragment, language-switch destinations, language metadata, portable asset paths, JSON, and inventory counts. It verifies that the report translation retains the original section anchors, citations, tables, paragraphs, and numerical facts. It also checks glossary translation completeness, reference IDs, term destinations, and safe annotation of prose, and verifies that committed generated pages match the source.

For browser smoke tests, install Playwright in a development environment, start the preview server, and run `node website/tests/browser.cjs`. Repeat with `SITE_URL=http://127.0.0.1:8766/es/` for Spanish. The test accepts `SITE_URL` (default `http://127.0.0.1:8766/`), `CHROME_PATH` (optional installed Chromium executable), and `SCREENSHOT_DIR` (optional screenshot directory). Browser tests cover desktop/mobile overflow, scripts, navigation, localized search/filtering, resource disclosures, report anchors, keyboard behavior, and switching languages with and without JavaScript.

Run `node website/tests/glossary.cjs` for each language with the same environment options. It checks cell-name explanations at four viewport widths, modal focus containment and restoration, Escape/close/backdrop/touch interactions, publication links, glossary search/topics/deep links, language changes, and the no-JavaScript reading fallback. Reference URLs were checked against the primary educational, cell-repository, and software-documentation sources on 11 October 2026; collected-study links reuse the existing publication records.

Run `node website/tests/hero.cjs` with the same environment options and the English root `SITE_URL`; it covers both languages. It verifies actual GIF motion, edge masks, keyboard pause/play, reduced-motion preferences, offscreen pausing, responsive layout, and still-image fallbacks without JavaScript or when the GIF cannot load.

## Publication

The public site is hosted at https://venettov.github.io/EnhancersResearch/ and its Spanish version at https://venettov.github.io/EnhancersResearch/es/. `Publish research website` publishes website-related changes merged or pushed to `main`, and also supports manual runs. It uploads only `docs/`; research-data-only changes do not trigger publication.

GitHub Pages is configured with **GitHub Actions** as its source. Review and validate website changes before merging them into `main`. Follow the resulting **Publish research website** run for deployment status. To redeploy the current site manually, run that workflow from `main`. See [GitHub's Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages).
