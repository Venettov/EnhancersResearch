/* Real-browser checks for the saved comparison explorer and the data guide. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const base=(process.env.SITE_URL||'http://127.0.0.1:8766/').replace(/\/?$/,'/');
const screenshots=process.env.SCREENSHOT_DIR;
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 try{
  for(const language of ['en','es']){
   const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
   const page=await context.newPage(),errors=[],requests=[];
   page.on('pageerror',e=>errors.push(e.message));context.on('request',r=>requests.push(r.url()));
   const prefix=base+(language==='es'?'es/':'');
   await page.goto(prefix+'reproduce.html');await page.locator('[data-explorer-panel]').waitFor({state:'visible'});
   assert.equal(await page.locator('[data-explorer-rows] tr').count(),8);
   const cells=page.locator('[data-agreement-matrix] button'),counts=[78,3,2,0,70,3,0,0,44];
   assert.deepEqual((await cells.allTextContents()).map(Number),counts);
   for(let i=0;i<counts.length;i++){
    await cells.nth(i).click();assert.equal(await page.locator('[data-explorer-rows] tr').count(),counts[i]);
    assert.equal(await cells.nth(i).getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('[data-explorer-empty]').isVisible(),counts[i]===0);
   }
   await page.locator('[data-explorer-all]').click();assert.equal(await page.locator('[data-explorer-rows] tr').count(),200);
   await page.locator('[data-explorer-different]').focus();await page.keyboard.press('Enter');
   assert.equal(await page.locator('[data-explorer-rows] tr').count(),8);
   const ids=await page.locator('[data-explorer-rows] th').allTextContents();assert(ids.includes('probe_0040'));
   await page.locator('#data-guide summary').click();
   const countRows=await page.locator('.fold-counts tbody tr').allTextContents();assert.equal(countRows.length,5);
   const root=path.resolve(__dirname,'../..');
   const summaries=[1,2].map(n=>JSON.parse(fs.readFileSync(path.join(root,`replication/ienhancer_2l/checkpoints/2026-10-13-svm-training/layer${n}_summary.json`),'utf8')));
   for(let i=0;i<5;i++){
    const displayed=(await page.locator('.fold-counts tbody tr').nth(i).locator('td').allTextContents()).map(v=>Number(v.replaceAll(',','')));
    assert.deepEqual(displayed,summaries.flatMap(s=>[s.outer_folds[i].train_n,s.outer_folds[i].test_n]));
   }
   for(const width of [1440,1024,768,390,320]){
    await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),`${language} overflow at ${width}`);
    assert(await page.locator('.comparison-sequences td').evaluateAll(cells=>cells.every(cell=>cell.scrollWidth<=cell.clientWidth+1)),`${language} overlapping comparison text at ${width}`);
    if(screenshots&&[1440,390].includes(width)){
     fs.mkdirSync(screenshots,{recursive:true});
     for(const [selector,name] of [['#data-guide','data-guide'],['[data-comparison-explorer]','comparison']])
      await page.locator(selector).screenshot({path:path.join(screenshots,`${name}-${language}-${width}.png`)});
    }
   }
   await page.goto(prefix+'research.html#independent-evaluation');
   assert(await page.locator('#independent-evaluation').isVisible());
   assert.equal(await page.locator('#independent-evaluation a[href^="https://github.com/"]').count(),3);
   assert(!(await page.locator('#roadmap').textContent()).includes(language==='es'?'Definir una evaluación':'Define an independent'));
   assert.deepEqual(errors,[]);assert(requests.every(url=>url.startsWith(base)));
   await context.close();
  }
  const nojs=await browser.newContext({javaScriptEnabled:false});const page=await nojs.newPage();await page.goto(base+'reproduce.html');
  assert.equal(await page.locator('[data-agreement-matrix] tbody td').count(),9);
  assert(await page.locator('#data-guide').isVisible());assert(await page.locator('[data-explorer-panel]').isHidden());await nojs.close();
  const failure=await browser.newContext();await failure.route('**/predictor_reference_200.json',route=>route.abort());
  const fallback=await failure.newPage();await fallback.goto(base+'reproduce.html');
  await fallback.waitForFunction(()=>document.querySelector('[data-explorer-status]').textContent.includes('could not load'));
  assert.equal(await fallback.locator('[data-agreement-matrix] button').count(),0);
  assert.equal(await fallback.locator('[data-agreement-matrix] tbody td').first().textContent(),'78');await failure.close();
  console.log('PASS: bilingual comparison cells, empty categories, all/disagreement filters, keyboard access, exact frozen fold counts, roadmap links, five viewport widths, no-JavaScript and failed-load fallback.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
