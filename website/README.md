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
- `data/`: small provenance snapshots from the research workspace. Absolute local-machine paths have been removed. These are dated snapshots, not a live audit.
- `../docs/`: generated, deployable output. Rebuild and commit it alongside source changes. Do not edit generated pages directly.

The foundational report retains its original date and scope. Later QC observations live in Research Notes. Local findings are not presented as new biological results. Dataset counts include publications, supplements, code, and model archives. Large datasets, downloaded PDFs, and model weights are excluded from the website; links lead to source publications and study guides.

The English/Spanish switch occupies the top-left utility bar and links to the same page in the other language. Spanish pages live under `docs/es/`; navigation stays in the chosen language. JavaScript preserves section anchors when switching, without redirecting shared URLs or requiring cookies. Both languages remain fully readable and switchable without JavaScript; JavaScript also adds the compact mobile menu and localized publication search/filtering. Resource sections use native HTML disclosure controls. The layout includes keyboard focus styles, a skip link, reduced-motion support, and print styles.

## Checks

`site-checks.yml` rebuilds and validates all twelve pages, every local link/fragment, language-switch destinations, language metadata, portable asset paths, JSON, and inventory counts. It verifies that the report translation retains the original section anchors, citations, tables, paragraphs, and numerical facts, and checks that committed generated pages match the source.

For browser smoke tests, install Playwright in a development environment, start the preview server, and run `node website/tests/browser.cjs`. Repeat with `SITE_URL=http://127.0.0.1:8766/es/` for Spanish. The test accepts `SITE_URL` (default `http://127.0.0.1:8766/`), `CHROME_PATH` (optional installed Chromium executable), and `SCREENSHOT_DIR` (optional screenshot directory). Browser tests cover desktop/mobile overflow, scripts, navigation, localized search/filtering, resource disclosures, report anchors, keyboard behavior, and switching languages with and without JavaScript.

## Publication

The public site is hosted at https://venettov.github.io/EnhancersResearch/ and its Spanish version at https://venettov.github.io/EnhancersResearch/es/. `Publish research website` publishes website-related changes merged or pushed to `main`, and also supports manual runs. It uploads only `docs/`; research-data-only changes do not trigger publication.

GitHub Pages is configured with **GitHub Actions** as its source. Review and validate website changes before merging them into `main`. Follow the resulting **Publish research website** run for deployment status. To redeploy the current site manually, run that workflow from `main`. See [GitHub's Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages).
