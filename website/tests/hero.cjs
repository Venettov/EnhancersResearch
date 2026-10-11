/* Browser checks for the animated home-page illustration and static fallbacks. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = (process.env.SITE_URL || 'http://127.0.0.1:8766/').replace(/\/?$/, '/');
const screenshotDir = process.env.SCREENSHOT_DIR;

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'no-preference' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const states = () => page.locator('.research-animation').evaluate(el => el.getAnimations({ subtree: true }).map(a => a.playState));
    const transform = () => page.locator('.dna-orbit').evaluate(el => getComputedStyle(el).transform);
    if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });
    for (const language of ['en', 'es']) {
      const url = base + (language === 'es' ? 'es/' : '');
      await page.goto(url);
      const visual = page.locator('.hero-visual');
      const toggle = visual.locator('[data-motion-toggle]');
      await visual.scrollIntoViewIfNeeded();
      await page.waitForFunction(() => document.querySelector('.hero-visual').dataset.motion === 'running');
      assert(await toggle.isVisible());
      assert.equal(await toggle.textContent(), language === 'es' ? 'Pausar animación' : 'Pause animation');
      const before = await transform();
      await page.waitForTimeout(300);
      assert.notEqual(await transform(), before, 'The illustration visibly animates');
      assert((await states()).length > 0);
      assert((await states()).every(state => state === 'running'));

      // Keyboard pause freezes the actual animation, not just the button label.
      await toggle.focus();
      await page.keyboard.press('Enter');
      await settle();
      assert.equal(await toggle.textContent(), language === 'es' ? 'Reproducir animación' : 'Play animation');
      assert((await states()).every(state => state === 'paused'));
      const frozen = await transform();
      await page.waitForTimeout(250);
      assert.equal(await transform(), frozen);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await settle();
      assert.equal(await toggle.isVisible(), false);
      assert((await states()).every(state => state !== 'running'));
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await settle();
      assert.equal(await toggle.textContent(), language === 'es' ? 'Reproducir animación' : 'Play animation', 'An explicit pause survives preference changes');
      await toggle.click();
      await settle();
      assert((await states()).every(state => state === 'running'));

      await page.locator('.site-footer').scrollIntoViewIfNeeded();
      await page.waitForFunction(() => document.querySelector('.hero-visual').dataset.motion === 'paused');
      await visual.scrollIntoViewIfNeeded();
      await page.waitForFunction(() => document.querySelector('.hero-visual').dataset.motion === 'running');
      for (const width of [1440, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 1000 });
        await visual.scrollIntoViewIfNeeded();
        assert(await toggle.isVisible());
        const fits = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
        assert(fits, `Home page overflows at ${width}px (${language})`);
        if (screenshotDir && [1440, 390].includes(width)) {
          await visual.screenshot({ path: path.join(screenshotDir, `${language}-visual-${width}.png`) });
          if (width === 1440) await page.locator('.hero').screenshot({ path: path.join(screenshotDir, `${language}-hero.png`) });
        }
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
    }

    // A visitor requesting less motion gets the complete diagram immediately.
    const reduced = await browser.newContext({ reducedMotion: 'reduce' });
    const quiet = await reduced.newPage();
    await quiet.goto(base);
    assert(await quiet.locator('.research-animation').isVisible());
    assert.equal(await quiet.locator('[data-motion-toggle]').isVisible(), false);
    assert(await quiet.locator('.research-animation').evaluate(el => el.getAnimations({ subtree: true }).every(a => a.playState !== 'running')));
    await reduced.close();

    const noJS = await browser.newContext({ javaScriptEnabled: false, reducedMotion: 'no-preference' });
    const fallback = await noJS.newPage();
    await fallback.goto(base + 'es/');
    assert(await fallback.locator('.research-animation').isVisible());
    assert.equal(await fallback.locator('[data-motion-toggle]').isVisible(), false);
    assert(await fallback.locator('.research-animation').evaluate(el => el.getAnimations({ subtree: true }).every(a => a.playState === 'paused')));
    assert((await fallback.locator('figcaption').textContent()).includes('no son datos medidos'));
    await noJS.close();
    assert.deepEqual(errors, []);
    console.log('PASS: bilingual visible animation, keyboard pause/play, reduced-motion changes, offscreen pause, four viewport widths, and static no-JavaScript fallback.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
