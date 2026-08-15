#!/usr/bin/env node
// sanity.mjs — render a handful of key timestamps to PNGs for eyeballing before
// committing to the full ~7-minute render. Catches layout collisions cheaply.
import { createServer } from 'node:http';
import { readFileSync, mkdirSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';

let chromium;
try { ({ chromium } = await import('playwright')); }
catch {
  try { ({ chromium } = await import('playwright-core')); }
  catch { ({ chromium } = (await import('/opt/node22/lib/node_modules/playwright/index.js')).default); }
}

const HERE = new URL('.', import.meta.url).pathname;
const ROOT = resolve(HERE, '..');
mkdirSync(join(HERE, 'sanity'), { recursive: true });
const W = 1920, H = 1080;
const types = { '.html':'text/html', '.woff2':'font/woff2', '.png':'image/png', '.js':'text/javascript', '.css':'text/css', '.mjs':'text/javascript', '.json':'application/json' };
const server = createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  const fp = join(ROOT, p === '/' ? '/film/film.html' : p);
  try { const body = readFileSync(fp); res.writeHead(200, { 'content-type': types[extname(fp)] || 'application/octet-stream' }); res.end(body); }
  catch { res.writeHead(404); res.end('404'); }
});
await new Promise(r => server.listen(7797, r));

let browser;
try { browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); }
catch { browser = await chromium.launch(); }
const page = await browser.newPage({ viewport: { width: W, height: H } });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
await page.addInitScript(() => {
  window.__filmT = 0;
  const rafs = new Set(); let id = 1;
  window.requestAnimationFrame = cb => { const i = id++; rafs.add({ i, cb }); return i; };
  window.__flushRaf = () => { const snap = [...rafs]; rafs.clear(); for (const r of snap) try { r.cb(window.__filmT * 1000); } catch (e) {} };
});
await page.goto('http://127.0.0.1:7797/film/film.html', { waitUntil: 'load' });
await page.waitForFunction(() => window.__ready === true, undefined, { polling: 200, timeout: 15000 });
await page.evaluate(() => document.fonts.ready);

const TS = [62, 152, 158, 162, 163, 164];
for (const t of TS) {
  await page.evaluate(tt => { window.__filmT = tt; window.__flushRaf(); window.__flushRaf(); }, t);
  await page.screenshot({ path: join(HERE, 'sanity', `t-${String(t).padStart(6,'0')}.png`) });
  process.stdout.write(`  sampled t=${t}s\n`);
}
if (errors.length) console.log('PAGE ERRORS:', errors.slice(0, 5));
else console.log('  no page errors.');
await browser.close(); server.close();
