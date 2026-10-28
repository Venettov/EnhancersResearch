/* Run after building and serving docs. Requires Playwright and Chromium. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = (process.env.SITE_URL || 'http://127.0.0.1:8766/').replace(/\/?$/, '/');
const root = path.resolve(__dirname, '../..');
const sample = fs.readFileSync(path.join(root, 'website/data/ienhancer_2l_server_200_queries.fasta'), 'utf8');
const reference = JSON.parse(fs.readFileSync(path.join(root, 'website/data/predictor_reference_200.json'), 'utf8'));
const sequence = sample.split('\n')[1];
const screenshots = process.env.SCREENSHOT_DIR;
const waitDone = page => page.locator('[data-results]').waitFor({state:'visible',timeout:60000});

(async () => {
 const browser = await chromium.launch({headless:true,...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {})});
 const reports = [];
 try {
  for (const language of ['en','es']) {
   const context = await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
   const page = await context.newPage();
   const errors = [], requests = [];
   page.on('pageerror', e => errors.push(e.message));
   context.on('request', r => requests.push({url:r.url(),method:r.method(),postData:r.postData()}));
   await page.goto(`${base}${language === 'es' ? 'es/' : ''}predictor.html`);
   await page.waitForFunction(() => !document.querySelector('fieldset').disabled);
   for (const width of [1440,1024,768,390,320]) {
    await page.setViewportSize({width,height:1000});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), `${language} overflow at ${width}`);
    if (screenshots && [1440,390].includes(width)) {
     fs.mkdirSync(screenshots,{recursive:true});
     await page.screenshot({path:path.join(screenshots,`predictor-${language}-input-${width}.png`),fullPage:true});
    }
   }
   await page.setViewportSize({width:1440,height:1000});
   await page.locator('[data-example="200"]').click();
   await page.waitForFunction(() => !document.querySelector('fieldset').disabled);
   assert((await page.locator('textarea').inputValue()).startsWith('>probe_0001'));
   const started = Date.now();
   await page.locator('[type="submit"]').click();await waitDone(page);
   assert.equal(await page.locator('[data-python-agreement]').textContent(),'200 / 200');
   assert.equal(await page.locator('[data-author-agreement]').textContent(),'192 / 200 (96.0%)');
   for (const [label,n] of [['strong',78],['weak',73],['non-enhancer',49]])
    assert.equal(await page.locator(`[data-count="${label}"]`).textContent(),String(n));
   const downloadWait = page.waitForEvent('download');await page.locator('[data-download]').click();
   const download = await downloadWait;
   const text = fs.readFileSync(await download.path(),'utf8');
   const lines=text.trim().split(/\r?\n/);assert.equal(lines.length,201);
   let maxError=0;
   lines.slice(1).forEach((line,i) => {
    const cells=line.slice(1,-1).split('","');
    assert.equal(cells[1],reference[i].probe_id);
    assert.equal(cells[2],reference[i].sequence_sha256);
    assert.equal(cells[3],reference[i].local_class);
    maxError=Math.max(maxError,Math.abs(Number(cells[4])-Number(reference[i].local_enhancer_score)));
    if(reference[i].local_strength_score) maxError=Math.max(maxError,Math.abs(Number(cells[5])-Number(reference[i].local_strength_score)));
    else assert.equal(cells[5],'');
   });assert(maxError<1e-6);
   await page.locator('[data-differences]').check();assert.equal(await page.locator('tbody tr').count(),8);
   // Search, class filters, and sorting compose without changing the underlying batch.
   await page.locator('[data-class-filter]').selectOption('weak');
   assert.equal(await page.locator('tbody tr').count(),3);
   await page.locator('[data-result-search]').fill('PROBE_0040');
   assert.equal(await page.locator('tbody tr').count(),1);
   assert.equal(await page.locator('tbody th').textContent(),'probe_0040');
   await page.locator('[data-result-search]').fill('no-such-sequence');
   assert.equal(await page.locator('tbody tr').count(),0);assert(await page.locator('[data-no-matches]').isVisible());
   assert.equal(await page.locator('[data-bar-value="strong"]').textContent(),'78 (39.0%)');
   assert.equal(await page.locator('[data-bar-value="weak"]').textContent(),'73 (36.5%)');
   assert.equal(await page.locator('[data-bar-value="non-enhancer"]').textContent(),'49 (24.5%)');
   // Export always contains every input, even when filters hide every row.
   const reportWait=page.waitForEvent('download');await page.locator('[data-report]').click();
   const reportDownload=await reportWait, reportHtml=fs.readFileSync(await reportDownload.path(),'utf8');
   assert.equal(reportDownload.suggestedFilename(),'ienhancer-report.html');
   const reportPage=await context.newPage();
   await reportPage.route('**/report-preview.html',route=>route.fulfill({contentType:'text/html',body:reportHtml}));
   await reportPage.goto(base+'report-preview.html');
   assert.equal(await reportPage.evaluate(()=>document.characterSet),'UTF-8');
   assert((await reportPage.locator('body').textContent()).includes(language==='es'?'Predicción guardada de los autores':'Authors’ saved prediction'));
   assert.equal(await reportPage.locator('tbody tr').count(),200);
   assert.equal(await reportPage.locator('tbody .hash').first().textContent(),reference[0].sequence_sha256);
   assert((await reportPage.locator('body').textContent()).includes('192/200 (96.0%)'));
   assert((await reportPage.locator('code').textContent()).includes('ienhancer-primary'));
   assert.equal(await reportPage.locator('script,img,iframe').count(),0);
   assert(!reportHtml.includes(sequence));
   assert.equal(await reportPage.locator('html').getAttribute('lang'),language);
   if(screenshots){await reportPage.emulateMedia({media:'print'});await reportPage.screenshot({path:path.join(screenshots,`prediction-report-${language}.png`)});}
   await reportPage.close();
   await page.locator('[data-reset-filters]').click();assert.equal(await page.locator('tbody tr').count(),200);
   for(const value of ['layer1-desc','layer1-asc','layer2-desc','layer2-asc']){
    await page.locator('[data-score-sort]').selectOption(value);
    const column=value.startsWith('layer1')?4:5;
    const values=await page.locator(`tbody td:nth-child(${column})`).allTextContents();
    const numbers=values.filter(v=>v!=='—').map(Number), descending=value.endsWith('desc');
    assert.equal(values.length,200);
    numbers.slice(1).forEach((n,i)=>assert(descending?n<=numbers[i]:n>=numbers[i]));
    if(column===5)assert(values.slice(numbers.length).every(v=>v==='—'));
   }
   await page.locator('[data-reset-filters]').click();await page.locator('[data-differences]').check();
   if(screenshots) for(const width of [1440,390]){
    await page.setViewportSize({width,height:1000});
    await page.locator('[data-results]').screenshot({path:path.join(screenshots,`predictor-${language}-results-${width}.png`)});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1));
   }
   reports.push({language,sample:200,pythonMatches:200,savedAuthorMatches:192,maxScoreError:maxError,elapsedMs:Date.now()-started});
   await page.locator('textarea').fill('>invalid\nACGT');
   assert(await page.locator('[data-results]').isHidden());
   assert.equal(await page.locator('[data-report]').getAttribute('href'),null);
   await page.locator('[type="submit"]').click();assert(await page.locator('[data-error]').isVisible());
   assert((await page.locator('[data-error]').textContent()).includes('200'));
   await page.locator('[data-example="3"]').click();
   await page.waitForFunction(()=>!document.querySelector('fieldset').disabled);
   await page.locator('[type="submit"]').click();await waitDone(page);
   assert.equal(await page.locator('tbody tr').count(),3);
   for(const label of ['strong','weak','non-enhancer'])assert.equal(await page.locator(`[data-count="${label}"]`).textContent(),'1');
   // Upload a wrapped/lowercase sequence and duplicate hostile identifiers. Never use innerHTML.
   const header='<img src=x onerror=alert(1)>';
   await page.locator('[type="file"]').setInputFiles({name:'test.fasta',mimeType:'text/plain',buffer:Buffer.from(`>${header}\n${sequence.slice(0,100).toLowerCase()}\n${sequence.slice(100)}\n>${header}\n${sequence}`)});
   await page.waitForFunction(()=>!document.querySelector('fieldset').disabled);
   await page.locator('[type="submit"]').click();await waitDone(page);
   assert.equal(await page.locator('tbody tr').count(),2);assert.equal(await page.locator('tbody img').count(),0);
   assert.equal(await page.locator('tbody th').first().textContent(),header);
   assert(await page.locator('[data-comparison]').isHidden());
   const unsafeWait=page.waitForEvent('download');await page.locator('[data-report]').click();
   const unsafeHtml=fs.readFileSync(await (await unsafeWait).path(),'utf8');
   const unsafeReport=await context.newPage();
   await unsafeReport.route('**/report-preview.html',route=>route.fulfill({contentType:'text/html',body:unsafeHtml}));
   await unsafeReport.goto(base+'report-preview.html');
   assert.equal(await unsafeReport.locator('tbody tr').count(),2);
   assert.equal(await unsafeReport.locator('img,script,iframe').count(),0);
   assert((await unsafeReport.locator('tbody th').first().textContent()).startsWith(header));
   assert(!(await unsafeReport.locator('body').textContent()).includes('192/200'));
   await unsafeReport.close();
   // New arbitrary DNA must produce a genuine prediction, independently of saved example labels.
   await page.locator('textarea').fill('>novel_test\n'+'ACGT'.repeat(50));
   await page.locator('[type="submit"]').click();await waitDone(page);
   assert.equal(await page.locator('tbody th').textContent(),'novel_test');
   assert(await page.locator('[data-comparison]').isHidden());
   assert.deepEqual(errors,[]);
   assert(requests.every(r=>r.method==='GET'&&!r.postData));
   assert(requests.every(r=>r.url.startsWith(base)));
   assert(!requests.some(r=>r.url.includes('novel_test')||r.url.includes(sequence)));
   await context.close();
  }
  const context=await browser.newContext({reducedMotion:'reduce'}), page=await context.newPage();
  const address=base+'predictor.html';
  // Cancellation during a model download must not deliver stale results later.
  await context.route('**/*.json.gz',async route=>{await new Promise(r=>setTimeout(r,500));try{await route.continue()}catch{}});
  await page.goto(address);await page.locator('textarea').fill(sample);
  await page.locator('[type="submit"]').click();await page.locator('[data-cancel]').click();
  assert((await page.locator('[data-status]').textContent()).includes('Cancelled'));
  await page.waitForTimeout(700);assert(await page.locator('[data-results]').isHidden());
  await context.unroute('**/*.json.gz');
  // A bad package must fail its integrity check; a normal retry must recover.
  await context.route('**/*.json.gz',route=>route.fulfill({status:200,body:'invalid-model'}));
  await page.locator('[type="submit"]').click();await page.locator('[data-error]').waitFor({state:'visible'});
  assert((await page.locator('[data-error]').textContent()).includes('integrity'));
  assert(await page.locator('[data-results]').isHidden());await context.unroute('**/*.json.gz');
  await page.locator('[type="submit"]').click();await waitDone(page);
  await page.reload();await context.route('**/predictor_manifest.json',route=>route.abort());
  await page.locator('textarea').fill('>one\n'+sequence);await page.locator('[type="submit"]').click();
  await page.locator('[data-error]').waitFor({state:'visible'});assert((await page.locator('[data-error]').textContent()).includes('could not load'));
  assert.equal(await page.locator('fieldset').evaluate(el=>el.disabled),false);await context.close();
  const disabled=await browser.newContext({javaScriptEnabled:false});const nojs=await disabled.newPage();await nojs.goto(address);
  assert(await nojs.locator('fieldset').evaluate(el=>el.disabled));assert(await nojs.locator('noscript a').first().isVisible());await disabled.close();
  const unsupported=await browser.newContext();await unsupported.addInitScript(()=>{window.DecompressionStream=undefined;delete window.DecompressionStream;});
  const oldBrowser=await unsupported.newPage();await oldBrowser.goto(address);assert(await oldBrowser.locator('fieldset').evaluate(el=>el.disabled));
  assert((await oldBrowser.locator('[data-status]').textContent()).includes('current browser'));await unsupported.close();
  console.log(JSON.stringify({status:'passed',runs:reports,checks:'200 real worker predictions per language; CSV scores/hashes; composable search, class and disagreement filters; score sorting with missing values last; full-batch charts and UTF-8 HTML reports; hostile-identifier escaping; responsive layouts; uploads; novel DNA; cancellation; integrity/load failures; no network uploads; JavaScript/API fallback'},null,2));
 } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exit(1)});
