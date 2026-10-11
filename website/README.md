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
- `assets/`: styles, progressive-enhancement JavaScript, and original SVG illustrations.
- `data/`: small provenance snapshots from the research workspace. Absolute local-machine paths have been removed. These are dated snapshots, not a live audit.
- `../docs/`: generated, deployable output. Rebuild and commit it alongside source changes. Do not edit generated pages directly.

The foundational report retains its original date and scope. Later QC observations live in Research Notes. Local findings are not presented as new biological results. Dataset counts include publications, supplements, code, and model archives. Large datasets, downloaded PDFs, and model weights are excluded from the website; links lead to source publications and study guides.

The site remains readable without JavaScript; JavaScript adds the compact mobile menu and publication search/filtering. Resource sections use native HTML disclosure controls. The layout includes keyboard focus styles, a skip link, reduced-motion support, and print styles.

## Checks

`site-checks.yml` rebuilds and validates page structure, every local link/fragment, portable asset paths, JSON, and inventory counts. It also checks that committed generated pages match the source.

For browser smoke tests, install Playwright in a development environment, start the preview server, and run `node website/tests/browser.cjs`. The test accepts `SITE_URL` (default `http://127.0.0.1:8766/`), `CHROME_PATH` (optional installed Chromium executable), and `SCREENSHOT_DIR` (optional screenshot directory). Browser tests cover desktop/mobile overflow, scripts, navigation, search/filtering, resource disclosures, report anchors, keyboard behavior, and reading without JavaScript.

## Publication

The repository's visibility and Pages settings are unchanged. `Publish research website` is a **manual-only** GitHub Actions workflow, restricted to `main`, and uploads only `docs/`.

When ready to publish, review the site, merge the website branch, confirm that the repository's plan supports GitHub Pages, select **GitHub Actions** as the Pages source, and manually run **Publish research website** from `main`. A private source repository does not by itself make a Pages site private; review the intended site visibility before deployment. See [GitHub's Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages).
