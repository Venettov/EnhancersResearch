/* Browser checks for the seamless home-page GIF, edge fade and still fallback. */
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
    const waitForMotion = running => page.waitForFunction(expected => {
      const visual = document.querySelector('.hero-visual');
      const image = visual.querySelector('img');
      return visual.dataset.motion === (expected ? 'running' : 'paused') && image.complete && image.naturalWidth > 0;
    }, running);
    if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });
    for (const language of ['en', 'es']) {
      await page.goto(base + (language === 'es' ? 'es/' : ''));
      const visual = page.locator('.hero-visual');
      const animation = visual.locator('.hero-animation');
      const toggle = visual.locator('[data-motion-toggle]');
      await visual.scrollIntoViewIfNeeded();
      await waitForMotion(true);
      assert((await animation.getAttribute('src')).endsWith('dna-helix-loop.gif'));
      assert.equal(await toggle.textContent(), language === 'es' ? 'Pausar animación' : 'Pause animation');
      const first = await animation.screenshot();
      await page.waitForTimeout(400);
      assert.notDeepEqual(await animation.screenshot(), first, 'The GIF visibly animates');
      const mask = await animation.evaluate(el => ({ image: getComputedStyle(el).maskImage, composite: getComputedStyle(el).maskComposite }));
      assert(mask.image.includes('linear-gradient'));
      assert(mask.composite.includes('intersect'));

      await toggle.focus();
      await page.keyboard.press('Enter');
      await waitForMotion(false);
      assert((await animation.getAttribute('src')).endsWith('dna-helix-loop-poster.jpg'));
      assert.equal(await toggle.textContent(), language === 'es' ? 'Reproducir animación' : 'Play animation');
      const still = await animation.screenshot();
      await page.waitForTimeout(250);
      assert.deepEqual(await animation.screenshot(), still, 'Pausing shows a stable still image');
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.waitForFunction(() => document.querySelector('[data-motion-toggle]').hidden);
      await waitForMotion(false);
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await page.waitForFunction(() => !document.querySelector('[data-motion-toggle]').hidden);
      assert((await animation.getAttribute('src')).endsWith('.jpg'), 'An explicit pause survives preference changes');
      await toggle.click();
      await waitForMotion(true);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await waitForMotion(false);
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await waitForMotion(true);
      await page.locator('.site-footer').scrollIntoViewIfNeeded();
      await waitForMotion(false);
      await visual.scrollIntoViewIfNeeded();
      await waitForMotion(true);

      for (const width of [1440, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 1000 });
        await visual.scrollIntoViewIfNeeded();
        assert(await toggle.isVisible());
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), `Home page overflows at ${width}px (${language})`);
        const frame = await animation.boundingBox();
        assert(Math.abs(frame.width / frame.height - 16 / 9) < 0.01);
        if (screenshotDir && [1440, 390].includes(width)) {
          await visual.screenshot({ path: path.join(screenshotDir, `${language}-visual-${width}.png`) });
          if (width === 1440) await page.locator('.hero').screenshot({ path: path.join(screenshotDir, `${language}-hero.png`) });
        }
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
    }

    for (const options of [{reducedMotion:'reduce'}, {javaScriptEnabled:false}]) {
      const fallbackContext = await browser.newContext(options);
      const fallback = await fallbackContext.newPage();
      const requests = [];
      fallback.on('request', request => requests.push(request.url()));
      await fallback.goto(base + 'es/');
      assert(await fallback.locator('.hero-animation').isVisible());
      assert.equal(await fallback.locator('[data-motion-toggle]').isVisible(), false);
      assert((await fallback.locator('.hero-animation').getAttribute('src')).endsWith('.jpg'));
      assert.equal(requests.some(url => url.endsWith('/dna-helix-loop.gif')), false, 'The GIF is not fetched for a still fallback');
      await fallbackContext.close();
    }

    // A failed GIF download leaves the readable poster in place.
    const failedContext = await browser.newContext({reducedMotion:'no-preference'});
    await failedContext.route('**/dna-helix-loop.gif', route => route.abort());
    const failed = await failedContext.newPage();
    failed.on('pageerror', error => errors.push(error.message));
    await failed.goto(base);
    await failed.locator('.hero-visual').scrollIntoViewIfNeeded();
    await failed.waitForLoadState('networkidle');
    assert((await failed.locator('.hero-animation').getAttribute('src')).endsWith('.jpg'));
    assert(await failed.locator('.hero-animation').evaluate(el => el.complete && el.naturalWidth > 0));
    assert.equal(await failed.locator('[data-motion-toggle]').isVisible(), false);
    await failedContext.close();
    assert.deepEqual(errors, []);
    console.log('PASS: bilingual GIF motion, feathered edges, keyboard pause/play, reduced motion, offscreen pause, four viewport widths, no-JavaScript still, and failed-download fallback.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
