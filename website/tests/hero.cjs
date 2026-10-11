/* Browser checks for the five-second home-page video and playback fallbacks. */
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
    const time = () => page.locator('.hero-video').evaluate(el => el.currentTime);
    const waitForPaused = paused => page.waitForFunction(expected => {
      const video = document.querySelector('.hero-video');
      return video.paused === expected && document.querySelector('.hero-visual').dataset.motion === (expected ? 'paused' : 'running');
    }, paused);
    if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });
    for (const language of ['en', 'es']) {
      await page.goto(base + (language === 'es' ? 'es/' : ''));
      const visual = page.locator('.hero-visual');
      const video = visual.locator('video');
      const toggle = visual.locator('[data-motion-toggle]');
      await visual.scrollIntoViewIfNeeded();
      await page.waitForFunction(() => document.querySelector('.hero-video').readyState >= 2);
      await waitForPaused(false);
      const media = await video.evaluate(el => ({ duration: el.duration, muted: el.muted, loop: el.loop, inline: el.playsInline, width: el.videoWidth, height: el.videoHeight }));
      assert(Math.abs(media.duration - 5) < 1 / 24, `Expected a five-second clip, got ${media.duration}`);
      assert(media.muted && media.loop && media.inline);
      assert.equal(media.width, 1280);
      assert.equal(media.height, 720);
      assert.equal(await toggle.textContent(), language === 'es' ? 'Pausar video' : 'Pause video');
      await video.evaluate(el => { el.currentTime = 1; });
      const before = await time();
      await page.waitForFunction(t => document.querySelector('.hero-video').currentTime > t + 0.15, before);
      await video.evaluate(el => { el.currentTime = 4.8; });
      await page.waitForFunction(() => document.querySelector('.hero-video').currentTime < 1);
      assert.equal(await video.evaluate(el => el.ended), false, 'The clip loops back to its opening');

      // Keyboard pause freezes actual video time, not just the button label.
      await toggle.focus();
      await page.keyboard.press('Enter');
      await waitForPaused(true);
      assert.equal(await toggle.textContent(), language === 'es' ? 'Reproducir video' : 'Play video');
      const frozen = await time();
      await page.waitForTimeout(250);
      assert.equal(await time(), frozen);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.waitForFunction(() => document.querySelector('[data-motion-toggle]').hidden);
      await waitForPaused(true);
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await page.waitForFunction(() => !document.querySelector('[data-motion-toggle]').hidden);
      assert.equal(await video.evaluate(el => el.paused), true, 'An explicit pause survives preference changes');
      await toggle.click();
      await waitForPaused(false);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await waitForPaused(true);
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await waitForPaused(false);

      await page.locator('.site-footer').scrollIntoViewIfNeeded();
      await waitForPaused(true);
      await visual.scrollIntoViewIfNeeded();
      await waitForPaused(false);
      for (const width of [1440, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 1000 });
        await visual.scrollIntoViewIfNeeded();
        assert(await toggle.isVisible());
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), `Home page overflows at ${width}px (${language})`);
        const frame = await video.boundingBox();
        assert(Math.abs(frame.width / frame.height - 16 / 9) < 0.01, 'The full original frame is retained');
        if (screenshotDir && [1440, 390].includes(width)) {
          await visual.screenshot({ path: path.join(screenshotDir, `${language}-visual-${width}.png`) });
          if (width === 1440) await page.locator('.hero').screenshot({ path: path.join(screenshotDir, `${language}-hero.png`) });
        }
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
    }

    // Reduced-motion users get a still frame, with no autoplay attribute.
    const reduced = await browser.newContext({ reducedMotion: 'reduce' });
    const quiet = await reduced.newPage();
    await quiet.goto(base);
    assert(await quiet.locator('.hero-video').isVisible());
    assert.equal(await quiet.locator('[data-motion-toggle]').isVisible(), false);
    assert(await quiet.locator('.hero-video').evaluate(el => el.paused && el.currentTime === 0 && !el.autoplay));
    assert.equal((await quiet.request.get(await quiet.locator('.hero-video').getAttribute('poster').then(p => new URL(p, base).href))).status(), 200);
    await reduced.close();

    const noJS = await browser.newContext({ javaScriptEnabled: false, reducedMotion: 'no-preference' });
    const fallback = await noJS.newPage();
    await fallback.goto(base + 'es/');
    assert(await fallback.locator('.hero-video').isVisible());
    assert.equal(await fallback.locator('[data-motion-toggle]').isVisible(), false);
    assert(await fallback.locator('.hero-video').evaluate(el => el.controls && el.paused && !el.autoplay && Boolean(el.poster)));
    assert((await fallback.locator('figcaption').textContent()).includes('no son datos medidos'));
    await noJS.close();

    // Browsers blocking autoplay must leave a usable manual-play button.
    const blocked = await browser.newContext({ reducedMotion: 'no-preference' });
    await blocked.addInitScript(() => {
      const original = HTMLMediaElement.prototype.play;
      let firstAttempt = true;
      HTMLMediaElement.prototype.play = function () {
        if (firstAttempt) { firstAttempt = false; return Promise.reject(new DOMException('Autoplay blocked', 'NotAllowedError')); }
        return original.call(this);
      };
    });
    const manual = await blocked.newPage();
    manual.on('pageerror', error => errors.push(error.message));
    await manual.goto(base);
    await manual.locator('.hero-visual').scrollIntoViewIfNeeded();
    await manual.waitForFunction(() => document.querySelector('[data-motion-toggle]').dataset.action === 'play');
    await manual.locator('[data-motion-toggle]').click();
    await manual.waitForFunction(() => !document.querySelector('.hero-video').paused && document.querySelector('.hero-video').currentTime > 0);
    await blocked.close();
    assert.deepEqual(errors, []);
    console.log('PASS: five-second bilingual video, actual playback and loop, keyboard pause/play, reduced-motion preferences, offscreen pause, four viewport widths, blocked-autoplay recovery, and native controls without JavaScript.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
