/* Built-site user journeys. Run: node tests/site-browser.cjs COURSE_REPO [...] */
const { chromium, expect } = require('@playwright/test');
const { default: AxeBuilder } = require('@axe-core/playwright');
const fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const assert = require('node:assert/strict');
const MIME = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.svg':'image/svg+xml','.woff2':'font/woff2','.png':'image/png','.ogg':'audio/ogg'};
function serve(root, prefix) {
  const server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (!pathname.startsWith(prefix)) { res.writeHead(404);res.end();return; }
    let file = path.resolve(root, '.' + '/' + pathname.slice(prefix.length));
    if (!file.startsWith(root + path.sep) && file !== root) {res.writeHead(403);res.end();return;}
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file=path.join(file,'index.html');
    if (!fs.existsSync(file)) {res.writeHead(404);res.end();return;}
    res.setHeader('Content-Type',MIME[path.extname(file)]||'application/octet-stream');
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(resolve=>server.listen(0,'127.0.0.1',()=>resolve(server)));
}
function walk(root) {return fs.readdirSync(root,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(root,e.name)):[path.join(root,e.name)]);}
(async()=>{
  const repos=process.argv.slice(2).map(x=>path.resolve(x));assert.ok(repos.length,'Give at least one built course repository');
  const output=process.env.BROWSER_ARTIFACTS||path.resolve('build/browser');fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true,channel:'chromium'});const results=[];
  try {
    for(const repo of repos) {
      const code=path.basename(repo), root=path.join(repo,'public');
      const config=fs.readFileSync(path.join(repo,'hugo.toml'),'utf8');
      const prefix=new URL(config.match(/^baseURL\s*=\s*"([^"]+)"/m)[1]).pathname;
      const server=await serve(root,prefix), origin=`http://127.0.0.1:${server.address().port}`, base=origin+prefix;
      const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
      const errors=[],failed=[],violations=[];
      await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
      page.on('pageerror',e=>errors.push(e.message));
      page.on('response',r=>{if(r.url().startsWith(origin)&&r.status()>=400)failed.push({url:r.url(),status:r.status()});});
      const record={code,pages:0,errors,failed,violations};results.push(record);
      try {
        const start=config.includes('defaultContentLanguageInSubdir = true')?'de/':'';
        const candidates=[start];
        const unit=walk(root).find(p=>/\/units\/[^/]+\/index.html$/.test(p)&&!/_exam|[-]exam/.test(p));
        if(unit)candidates.push(path.relative(root,path.dirname(unit)).split(path.sep).join('/')+'/');
        for(const name of ['search','materials','materiel'])if(fs.existsSync(path.join(root,name,'index.html')))candidates.push(name+'/');
        if(code==='ressources') candidates.push('de/overview/','en/overview/','fr/overview/');
        for(const destination of candidates) {
          await page.goto(base+destination);await page.evaluate(()=>document.fonts.ready);
          await expect(page.locator('#main-content')).toHaveCount(1);
          if(code==='ressources' && destination.endsWith('/overview/')) {
            const cards=page.locator('#ov-list .ov-card');
            await expect(cards.first()).toBeVisible();
            const all=await cards.count();assert.ok(all>10);
            const chip=page.locator('.ov-chip[data-id="lang:EN"]');
            await chip.click();await expect(chip).toHaveAttribute('aria-pressed','true');
            assert.ok(await cards.count()<all && await cards.count()>0);
            await page.locator('.ov-clear').click();await expect(cards).toHaveCount(all);
            const detail=page.locator('.ov-card-toggle').first();await detail.click();
            await expect(detail).toHaveAttribute('aria-expanded','true');
            const vendor=await page.locator('#overview-root').getAttribute('data-vendor');
            assert.equal(await page.evaluate(u=>performance.getEntriesByType('resource').some(r=>new URL(r.name).pathname===u),vendor),false,'graph loaded before requested');
            await page.locator('#ov-graph button').click();
            await expect(page.locator('#ov-graph canvas')).toBeVisible();
          }
          if(code==='efl' && destination==='materials/') {
            const cards=page.locator('#network-list > .network-card');
            const data=JSON.parse(fs.readFileSync(path.join(root,'materials/graph.json'),'utf8'));
            const total=data.nodes.filter(n=>n.type==='article').length;
            await expect(cards).toHaveCount(Math.min(60,total));
            while(await page.locator('[data-action="show-more"]').count()) await page.locator('[data-action="show-more"]').click();
            await expect(cards).toHaveCount(total);
            await page.locator('button[data-facet="type"][data-value="presentation"]').click();
            await expect(cards.first()).toBeVisible();await expect(cards.first().locator('a[download]')).toHaveCount(1);
            const download=await cards.first().locator('a[download]').getAttribute('href');
            assert.equal((await context.request.get(new URL(download,base).href)).status(),200);
            await page.locator('[data-action="reset"]').click();
            await page.locator('#network-search-input').fill('zznomaterial987');
            await expect(page.locator('.network-empty')).toBeVisible({timeout:15000});
            await page.locator('#network-search-input').fill('');await expect(cards).toHaveCount(Math.min(60,total));
            const vendor=await page.locator('#network-graph').getAttribute('data-module-url');
            assert.equal(await page.evaluate(u=>performance.getEntriesByType('resource').some(r=>new URL(r.name).pathname===u),vendor),false,'graph loaded before requested');
            await page.getByRole('button',{name:'Show network',exact:true}).click();
            await expect(page.locator('#network-graph canvas').first()).toBeVisible();
          }
          if(code==='fle' && destination==='materiel/') {
            await expect(page.locator('#network-cards > li').first()).toBeVisible();
            await page.getByRole('button',{name:'Afficher le réseau',exact:true}).click();
            await expect(page.locator('#network-graph canvas').first()).toBeVisible();
          }
          const report=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
          violations.push(...report.violations.map(v=>({page:destination,id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})));
          if(destination==='search/') {
            const query={efl:'hello',fle:'bonjour',daf:'Name'}[code]||'language';
            await page.getByRole('searchbox').fill(query);
            const link=page.locator('pagefind-results a').first();await expect(link).toBeVisible({timeout:15000});
            const href=await link.getAttribute('href');assert.ok(new URL(href,base).pathname.startsWith(prefix),href);
            const response=await context.request.get(new URL(href,base).href);assert.equal(response.status(),200);
          }
          await page.screenshot({path:path.join(output,`${code}-${destination.replaceAll('/','_')||'home'}-desktop.png`)});
          await page.setViewportSize({width:390,height:844});
          const menu=page.locator('.navigation-list');
          if(await menu.count())await expect(menu).toBeHidden();
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`${code}/${destination}: horizontal overflow`);
          await page.screenshot({path:path.join(output,`${code}-${destination.replaceAll('/','_')||'home'}-mobile.png`)});
          await page.setViewportSize({width:1440,height:1000});
        }
        await page.goto(base+start);
        const summary=page.locator('.navigation-dropdown summary').first();
        if(await summary.count()) {
          await summary.focus();await page.keyboard.press('Space');
          assert.equal(await summary.evaluate(e=>e.parentElement.open),true);
          await page.keyboard.press('Escape');assert.equal(await summary.evaluate(e=>e.parentElement.open),false);
        }
        await page.setViewportSize({width:390,height:844});
        const toggle=page.locator('#menu-toggle');
        if(await toggle.count()) {
          await expect(page.locator('.navigation-list')).toBeHidden();
          await toggle.focus();await page.keyboard.press('Space');await expect(toggle).toBeChecked();
          await expect(page.locator('.navigation-list')).toBeVisible();
        }
        if(code==='fle') {
          await page.goto(base+'materiel/');
          await expect(page.locator('#network-cards > li').first()).toBeVisible();
          await expect(page.locator('[data-facet=type] button').first()).toBeVisible();
        }
        const nojs=await browser.newContext({javaScriptEnabled:false});
        await nojs.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
        const plain=await nojs.newPage();await plain.goto(base+start);await expect(plain.locator('#main-content')).toHaveCount(1);await nojs.close();
        record.pages=candidates.length;
        console.log(`${code}: ${candidates.length} pages; ${violations.length} accessibility findings; ${errors.length} script errors; ${failed.length} failed requests`);
      } finally {await context.close();await new Promise(r=>server.close(r));}
    }
  } finally {await browser.close();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2)+'\n');}
  if(results.some(x=>x.errors.length||x.failed.length||x.violations.length))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
