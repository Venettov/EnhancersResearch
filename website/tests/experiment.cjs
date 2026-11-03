/* Integration checks for the published-data explorer and exact FASTA handoff. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const base = (process.env.SITE_URL || 'http://127.0.0.1:8767/').replace(/\/?$/, '/');
const root = path.resolve(__dirname, '../..');
const data = JSON.parse(fs.readFileSync(path.join(root,'website/data/lentimpra_demo_200.json'),'utf8'));
const sample = fs.readFileSync(path.join(root,'website/data/ienhancer_2l_server_200_queries.fasta'),'utf8');
const sequences = new Map(sample.split('>').slice(1).map(r=>{const lines=r.trim().split('\n');return [lines[0],lines.slice(1).join('')];}));
(async()=>{
 const browser = await chromium.launch({headless:true,...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {})});
 try {
  for(const lang of ['en','es']) {
   const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
   const page=await context.newPage(), errors=[],requests=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r));
   const prefix=base+(lang==='es'?'es/':'');
   await page.goto(prefix+'experiment.html');await page.locator('[data-experiment-panel]').waitFor({state:'visible'});
   const nav=await page.locator('#primary-navigation > a').evaluateAll(links=>links.map(a=>a.getAttribute('href')));
   assert.equal(nav[nav.indexOf('predictor.html')+1],'experiment.html');
   assert.equal(await page.locator('[data-experiment-rows] tr').count(),200);
   assert.equal(await page.locator('.plot-point').count(),185);
   const x=await page.locator('.plot-point[data-probe="probe_0001"]').getAttribute('cx');
   for(const cell of data.cells){
    await page.locator('#experiment-cell').selectOption(cell);
    assert.equal(await page.locator('.plot-point[data-probe="probe_0001"]').getAttribute('cx'),x);
    assert((await page.locator('[data-experiment-plot] svg').getAttribute('aria-label')).includes(cell));
   }
   await page.locator('#experiment-probe').selectOption('probe_0017');
   assert.equal(await page.locator('[data-sequence-activity] tr td:first-of-type').allTextContents().then(x=>x.join(',')),'—,—,—');
   assert.equal(await page.locator('.plot-point.is-selected').count(),0);
   await page.locator('#experiment-probe').selectOption('probe_0040');
   assert.equal(await page.locator('[data-sequence-activity] tr td:first-of-type').allTextContents().then(x=>x.join(',')),'0.617,-0.078,1.243');
   assert.equal(await page.locator('.plot-point.is-selected').count(),0);
   await page.locator('#experiment-coverage').selectOption('excluded');
   assert.equal(await page.locator('[data-experiment-rows] tr').count(),15);
   await page.locator('#experiment-coverage').selectOption('eligible');
   assert.equal(await page.locator('[data-experiment-rows] tr').count(),185);
   await page.locator('#experiment-search').fill('PROBE_0002');
   assert.equal(await page.locator('[data-experiment-rows] tr').count(),1);
   const button=page.locator('[data-experiment-rows] button');await button.focus();await page.keyboard.press('Enter');
   assert.equal(await page.locator('[data-probe-title]').textContent(),'probe_0002');
   assert(await button.evaluate(el=>el===document.activeElement));
   await page.locator('#experiment-search').fill('<img src=x onerror=alert(1)>');
   assert(await page.locator('[data-experiment-empty]').isVisible());
   assert.equal(await page.locator('.plot-point').count(),185);
   await page.locator('#experiment-search').fill('');
   await page.locator('#experiment-coverage').selectOption('all');
   await page.locator('.plot-point[data-probe="probe_0001"]').click();
   assert.equal(await page.locator('[data-probe-title]').textContent(),'probe_0001');
   for(const width of [1440,1024,768,390,320]){
    await page.setViewportSize({width,height:1000});
    await page.waitForFunction(()=>Math.abs(document.querySelector('[data-experiment-plot] svg').viewBox.baseVal.width-document.querySelector('[data-experiment-plot]').clientWidth)<2);
    const dim=await page.evaluate(()=>[document.documentElement.scrollWidth,document.documentElement.clientWidth]);
    assert(dim[0]<=dim[1]+1,`${lang} overflow at ${width}: ${dim}`);
    const detail=await page.locator('.experiment-detail .table-scroll').evaluate(el=>[el.scrollWidth,el.clientWidth]);
    assert(detail[0]<=detail[1]+1,`${lang} measurement table clips at ${width}: ${detail}`);
    if(process.env.SCREENSHOT_DIR && [1440,390].includes(width)){
     fs.mkdirSync(process.env.SCREENSHOT_DIR,{recursive:true});
     await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,`${lang}-experiment-${width}.png`),fullPage:true});
    }
   }
   await page.setViewportSize({width:1440,height:1000});
   await page.locator('#experiment-probe').selectOption('probe_0040');
   await page.locator('[data-predict-sequence]').click();
   await page.waitForFunction(()=>document.querySelector('#prediction-input').value.startsWith('>probe_0040'));
   assert.equal((await page.locator('#prediction-input').inputValue()).split('\n').slice(1).join(''),sequences.get('probe_0040'));
   assert.equal(await page.locator('[data-results]').isVisible(),false,'Does not auto-run predictions');
   await page.locator('.predictor-run').click();await page.locator('[data-results]').waitFor({state:'visible',timeout:60000});
   const score=Number(await page.locator('[data-results] tbody tr td').nth(2).textContent());
   assert(Math.abs(score-data.records.find(r=>r.probe_id==='probe_0040').layer1_score)<1e-7);
   await page.goto(prefix+'predictor.html?example=lentimpra');
   await page.waitForFunction(()=>document.querySelector('#prediction-input').value.split('>').length===201);
   assert.equal(await page.locator('#prediction-input').inputValue(),sample);
   assert.equal(await page.locator('[data-results]').isVisible(),false);
   await page.goto(prefix+'predictor.html?example=lentimpra&probe=unknown');
   await page.locator('[data-error]').waitFor({state:'visible'});
   assert.equal(await page.locator('#prediction-input').inputValue(),'');
   assert.deepEqual(errors,[]);
   assert(requests.every(r=>r.method()==='GET'),'No sequence submission');
   assert(requests.every(r=>r.url().startsWith(base)||r.url().startsWith('blob:')),'Only local assets requested');
   await context.close();
   const fallback=await browser.newContext({javaScriptEnabled:false});const nojs=await fallback.newPage();
   await nojs.goto(prefix+'experiment.html');assert(await nojs.locator('.experiment-correlations').isVisible());
   const csv=await nojs.request.get(new URL(lang==='es'?'../data/lentimpra_demo_200.csv':'data/lentimpra_demo_200.csv',prefix).href);
   assert(csv.ok());assert.equal((await csv.text()).trim().split('\n').length,201);await fallback.close();
   const broken=await browser.newContext();const errpage=await broken.newPage();
   await errpage.route('**/lentimpra_demo_200.json',r=>r.fulfill({status:503,body:'unavailable'}));
   await errpage.goto(prefix+'experiment.html');
   await errpage.waitForFunction(()=>/could not|No se pudo/.test(document.querySelector('[data-experiment-status]').textContent));
   assert.equal(await errpage.locator('[data-experiment-panel]').isVisible(),false);await broken.close();
   console.log(`PASS ${lang}: 200 rows, coverage/missingness, three-cell plot, keyboard search, mobile layout, exact FASTA handoff, saved-score parity, privacy, and fallbacks`);
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
