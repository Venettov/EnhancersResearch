/* Optional browser smoke test. Requires Playwright and a running static server. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = (process.env.SITE_URL || 'http://127.0.0.1:8766/').replace(/\/?$/, '/');
const screenshotDir = process.env.SCREENSHOT_DIR;
const pages = ['index', 'research', 'publications', 'resources', 'notes', 'strategy'];
const language = base.endsWith('/es/') ? 'es' : 'en';
const root = language === 'es' ? base.slice(0, -3) : base;

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.url().startsWith(base) && response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
    if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const slug of pages) {
        await page.goto(`${base}${slug}.html`);
        assert.equal(await page.locator('html').getAttribute('lang'), language);
        assert.equal(await page.locator('.language-switch a[aria-current="true"]').getAttribute('data-language'), language);
        assert.equal(await page.locator('h1').count(), 1);
        assert(await page.locator('h1').isVisible());
        const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
        assert(dimensions.scroll <= dimensions.client + 1, `${slug} overflows at ${width}px: ${JSON.stringify(dimensions)}`);
        if (screenshotDir && [1440, 390].includes(width)) {
          await page.screenshot({ path: path.join(screenshotDir, `${language}-${slug}-${width}.png`), fullPage: slug !== 'strategy' });
        }
      }
    }

    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${base}publications.html`);
    const visibleCount = () => page.locator('[data-publication]:visible').count();
    assert.equal(await visibleCount(), 8);
    for (const [type, count] of [['experimental', 3], ['annotation', 2], ['model', 3]]) {
      await page.locator(`[data-filter="${type}"]`).click();
      assert.equal(await visibleCount(), count);
      assert.equal(await page.locator(`[data-filter="${type}"]`).getAttribute('aria-pressed'), 'true');
      assert.equal(await page.locator('#publication-count').textContent(), language === 'es' ? `${count} de 8 trabajos recopilados` : `${count} of 8 collected works`);
    }
    await page.locator('[data-filter="all"]').click();
    await page.locator('#publication-search').fill('Fromel');
    assert.equal(await visibleCount(), 1, 'Search normalizes diacritics');
    await page.locator('#publication-search').fill('No matching publication xyz');
    assert.equal(await visibleCount(), 0);
    assert(await page.locator('#publication-empty').isVisible());
    await page.locator('[data-clear-search]').click();
    assert.equal(await visibleCount(), 8);
    assert(await page.locator('#publication-search').evaluate(element => element === document.activeElement));
    await page.locator('[data-filter="model"]').click();
    await page.locator('.reading-note a[href="#P02"]').click();
    await page.locator('#P02').waitFor({ state: 'visible' });
    assert(await page.locator('#P02').isVisible(), 'In-page reading links reveal filtered items');
    await page.locator('[data-filter="model"]').click();
    await page.locator('.reading-note a[href="#P02"]').click();
    assert(await page.locator('#P02').isVisible(), 'Repeated link to the same hash also reveals the item');

    await page.goto(`${base}resources.html`);
    assert.equal(await page.locator('details').count(), 7);
    const disclosure = page.locator('details').first();
    await disclosure.locator('summary').focus();
    await page.keyboard.press('Enter');
    assert(await disclosure.evaluate(element => element.open));
    assert(await disclosure.locator('.resource-body').isVisible());
    await disclosure.locator('summary').click();
    assert.equal(await disclosure.evaluate(element => element.open), false);

    await page.goto(`${base}strategy.html`);
    assert.equal(await page.locator('.report-toc ol a').count(), 12);
    await page.locator('.report-toc a[href="#8-analysis-design"]').click();
    assert(page.url().endsWith('#8-analysis-design'));
    const headingTop = await page.locator('[id="8-analysis-design"]').evaluate(element => element.getBoundingClientRect().top);
    assert(headingTop >= 0 && headingTop < 150, `Report anchor is visible: ${headingTop}`);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${base}index.html`);
    const menu = page.locator('.menu-toggle');
    const nav = page.locator('.primary-nav');
    assert(await menu.isVisible());
    assert.equal(await nav.isVisible(), false);
    await menu.click();
    assert(await nav.isVisible());
    await page.keyboard.press('Escape');
    assert.equal(await nav.isVisible(), false);
    assert(await menu.evaluate(element => element === document.activeElement));
    await menu.click();
    await nav.locator('a[href="research.html"]').click();
    assert(page.url().endsWith('research.html'));
    assert.equal(await nav.isVisible(), false);
    await page.goto(`${base}index.html`);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.className), 'skip-link');
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'main');

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const fallback = await noJS.newPage();
    await fallback.goto(`${base}publications.html`);
    assert.equal(await fallback.locator('[data-publication]:visible').count(), 8);
    assert(await fallback.locator('.primary-nav').isVisible());
    assert.equal(await fallback.locator('[data-publication-tools]').isVisible(), false);
    await fallback.locator(`[data-language="${language === 'es' ? 'en' : 'es'}"]`).click();
    assert.equal(await fallback.locator('html').getAttribute('lang'), language === 'es' ? 'en' : 'es', 'Language switching works without JavaScript');

    // Language switching preserves both the document and the report section.
    await page.goto(`${root}strategy.html#8-analysis-design`);
    await page.locator('[data-language="es"]').click();
    assert.equal(page.url(), `${root}es/strategy.html#8-analysis-design`);
    assert.equal(await page.locator('html').getAttribute('lang'), 'es');
    assert.equal(await page.locator('[id="8-analysis-design"]').textContent(), '8 Diseño del análisis');
    await page.locator('[data-language="en"]').click();
    assert.equal(page.url(), `${root}strategy.html#8-analysis-design`);
    await page.goto(`${root}es/index.html`);
    await page.locator('.menu-toggle').click();
    await page.locator('.primary-nav a[href="research.html"]').click();
    assert.equal(page.url(), `${root}es/research.html`, 'Navigation stays in the selected language');
    assert.deepEqual(errors, [], 'No page errors or local HTTP failures');
    await noJS.close();
    console.log(`PASS (${language}): six pages at four widths, localized controls, search/filtering, language and anchor preservation, mobile/keyboard navigation, no-JavaScript switching, and no page errors`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
