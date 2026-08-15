#!/usr/bin/env node
// sanity.mjs — render a handful of frames at key timestamps so the layout can be
// eyeballed before committing to the full ~10-minute render. Writes sanity-*.png.

import pkg from '/opt/node22/lib/node_modules/playwright/index.js';
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { extname, join } from 'node:path';

const { chromium } = pkg;
const HERE = new URL('.', import.meta.url).pathname;
const W = 1920, H = 1080, PORT = 7794;
const TIMES = [4, 18, 26, 33, 40, 55, 64, 74, 92, 100, 116, 124, 136, 143, 148];

const types = { '.html':'text/html', '.woff2':'font/woff2' };
const server = createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  const fp = join(HERE, p === '/' ? '/film.html' : p);
  try { res.writeHead(200, { 'content-type': types[extname(fp)] || 'application/octet-stream' }); res.end(readFileSync(fp)); }
  catch { res.writeHead(404); res.end('404'); }
});
await new Promise(r => server.listen(PORT, r));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: W, height: H } });
const page = await ctx.newPage();
const errors = []; page.on('pageerror', e => errors.push(String(e)));
await page.addInitScript(() => {
  const ANCHOR = 1700000000000;
  window.__filmT = 0;
  const _now = () => ANCHOR + Math.round(window.__filmT * 1000);
  Date.now = _now;
  const OD = Date;
  function FDate(...a){ return a.length===0 ? new OD(_now()) : new OD(...a); }
  FDate.now=_now; FDate.parse=OD.parse; FDate.UTC=OD.UTC; FDate.prototype=OD.prototype; window.Date=FDate;
  if (window.performance) performance.now = () => window.__filmT * 1000;
  const rafs=new Set(); let id=1;
  window.requestAnimationFrame=cb=>{const i=id++;rafs.add({i,cb});return i;};
  window.__flushRaf=()=>{const snap=[...rafs];rafs.clear();for(const r of snap)try{r.cb(window.__filmT*1000);}catch(e){}};
});
await page.goto('http://127.0.0.1:' + PORT + '/film.html', { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__ready === true, { timeout: 15000 });
await page.evaluate(() => document.fonts.ready);
for (const t of TIMES) {
  await page.evaluate(tt => { window.__filmT = tt; window.__flushRaf(); window.__flushRaf(); }, t);
  await page.screenshot({ path: join(HERE, `sanity-${String(t).padStart(3,'0')}.png`), clip: { x:0,y:0,width:W,height:H } });
  process.stdout.write(`  sanity-${String(t).padStart(3,'0')}.png\n`);
}
if (errors.length) console.log('PAGE ERRORS:', errors.slice(0,8));
await browser.close(); server.close();
