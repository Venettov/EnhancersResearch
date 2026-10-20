/* Interaction checks for the sourced, progressively enhanced reading aid. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const glossary = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'glossary.json'), 'utf8'));
const termCount = glossary.terms.length;
const modelCount = glossary.terms.filter(term => term.category === 'models').length;
const base = (process.env.SITE_URL || 'http://127.0.0.1:8766/').replace(/\/?$/, '/');
const es = base.endsWith('/es/');
const screenshotDir = process.env.SCREENSHOT_DIR;

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const dialog = page.locator('#term-dialog');
    if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(base);
      for (const id of ['hepg2', 'k562', 'wtc11']) {
        const link = page.locator(`.welcome [data-term="${id}"]`).first();
        await link.scrollIntoViewIfNeeded();
        await link.focus();
        const scroll = await page.evaluate(() => window.scrollY);
        await page.keyboard.press('Enter');
        assert(await dialog.isVisible());
        assert.equal(await dialog.getAttribute('aria-labelledby'), 'term-title');
        assert(await page.locator('#term-definition').textContent());
        assert(await page.locator('#term-context').textContent());
        assert((await page.locator('#term-sources a').count()) >= 1);
        assert.equal(await page.locator('#term-papers a').first().getAttribute('href'), 'publications.html#P02');
        assert(await page.locator('#term-title').evaluate(el => el === document.activeElement));
        const bounds = await dialog.boundingBox();
        assert(bounds.x >= 0 && bounds.x + bounds.width <= width + 1 && bounds.y >= 0 && bounds.y + bounds.height <= 845, 'Dialog stays within viewport');
        assert(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1), 'No horizontal dialog overflow');
        for (let step = 0; step < 12; step++) {
          await page.keyboard.press('Tab');
          assert(await dialog.evaluate(el => el.contains(document.activeElement)), 'Modal keeps keyboard focus inside');
        }
        if (screenshotDir && id === 'hepg2' && [1440, 390].includes(width)) {
          await dialog.evaluate(el => { el.scrollTop = 0; });
          await page.screenshot({ path: path.join(screenshotDir, `${es ? 'es' : 'en'}-explanation-${width}.png`) });
        }
        await page.keyboard.press('Escape');
        assert.equal(await dialog.isVisible(), false);
        assert(await link.evaluate(el => el === document.activeElement), 'Focus returns to selected term');
        assert(Math.abs(await page.evaluate(() => window.scrollY) - scroll) < 2, 'Reading position is preserved');
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${base}research.html`);
    const opener = page.locator('[data-term="hepg2"]').first();
    await opener.click();
    await page.locator('[data-term-close]').click();
    assert.equal(await dialog.isVisible(), false);
    await opener.click();
    await page.mouse.click(8, 8);
    assert.equal(await dialog.isVisible(), false, 'Backdrop dismisses');
    await opener.click();
    await page.locator('#term-papers a').first().click();
    assert(page.url().endsWith('publications.html#P02'));
    assert(await page.locator('#P02').isVisible());
    await page.goto(`${base}research.html`);
    await opener.click();
    await page.locator('#term-entry-link').click();
    assert(page.url().endsWith('glossary.html#term-hepg2'));
    assert(await page.locator('#term-hepg2').isVisible());
    assert.equal(await page.locator('[data-glossary-entry]').count(), termCount);
    const search = page.locator('#glossary-search');
    await search.fill(es ? 'celula' : 'cell');
    assert(await page.locator('#term-wtc11').isVisible(), 'Accent-insensitive search includes definitions');
    await search.fill('no-result-xyz');
    assert(await page.locator('#glossary-empty').isVisible());
    assert.equal(await page.locator('[data-glossary-entry]:visible').count(), 0);
    await page.locator('[data-glossary-clear]').click();
    assert.equal(await page.locator('[data-glossary-entry]:visible').count(), termCount);
    assert(await search.evaluate(el => el === document.activeElement));
    await page.locator('#glossary-topic').selectOption('models');
    assert.equal(await page.locator('[data-glossary-entry]:visible').count(), modelCount);
    await page.evaluate(() => { location.hash = 'term-wtc11'; });
    await page.locator('#term-wtc11').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#glossary-topic').inputValue(), 'all', 'Deep links reveal filtered entries');
    await page.locator(`[data-language="${es ? 'en' : 'es'}"]`).click();
    assert(page.url().endsWith('glossary.html#term-wtc11'));
    assert.equal(await page.locator('html').getAttribute('lang'), es ? 'en' : 'es');

    // Native text links still reach the full definitions without scripting.
    const noJS = await browser.newContext({ javaScriptEnabled: false });
    const fallback = await noJS.newPage();
    await fallback.goto(base);
    await fallback.locator('.welcome [data-term="hepg2"]').click();
    assert(fallback.url().endsWith('glossary.html#term-hepg2'));
    assert(await fallback.locator('#term-hepg2').isVisible());
    assert.equal(await fallback.locator('[data-glossary-entry]:visible').count(), termCount);
    assert.equal(await fallback.locator('[data-glossary-tools]').isVisible(), false);
    await noJS.close();

    // Exercise a real mobile touch event, not just a desktop mouse at a narrow width.
    const touch = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    const mobile = await touch.newPage();
    await mobile.goto(base);
    await mobile.locator('.welcome [data-term="wtc11"]').tap();
    assert(await mobile.locator('#term-dialog').isVisible());
    await mobile.locator('[data-term-close]').tap();
    assert.equal(await mobile.locator('#term-dialog').isVisible(), false);
    await touch.close();
    assert.deepEqual(errors, []);
    console.log(`PASS (${es ? 'es' : 'en'}): sourced cell explanations, four viewport sizes, focus containment/return, Escape/close/backdrop/touch, paper links, glossary search/topics/anchors, bilingual links and no-JS fallback`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
