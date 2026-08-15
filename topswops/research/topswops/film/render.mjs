#!/usr/bin/env node
// render.mjs — render film.html to PNG frames with a deterministic clock.
// 150 s × 24 fps = 3600 frames. Frames removed after the encode (see build.sh).
//
// The page is served over a tiny local HTTP server so its self-hosted woff2
// fonts load by relative path; Date.now()/requestAnimationFrame are overridden
// so each PNG is the page's exact state at t = frame / FPS.

import pkg from '/opt/node22/lib/node_modules/playwright/index.js';
import { createServer } from 'node:http';
import { readFileSync, mkdirSync } from 'node:fs';
import { extname, join } from 'node:path';

const { chromium } = pkg;
const HERE = new URL('.', import.meta.url).pathname;
const FRAMES = join(HERE, 'frames');
mkdirSync(FRAMES, { recursive: true });

const FPS = 24, DUR = 150, TOTAL = FPS * DUR, W = 1920, H = 1080, PORT = 7793;

const types = { '.html':'text/html', '.woff2':'font/woff2', '.png':'image/png', '.js':'text/javascript', '.css':'text/css' };
const server = createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  const fp = join(HERE, p === '/' ? '/film.html' : p);
  try { res.writeHead(200, { 'content-type': types[extname(fp)] || 'application/octet-stream' }); res.end(readFileSync(fp)); }
  catch { res.writeHead(404); res.end('404'); }
});
await new Promise(r => server.listen(PORT, r));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));

await page.addInitScript(() => {
  const ANCHOR = 1700000000000;
  window.__filmT = 0;
  const _now = () => ANCHOR + Math.round(window.__filmT * 1000);
  Date.now = _now;
  const OD = Date;
  function FDate(...a) { return a.length === 0 ? new OD(_now()) : new OD(...a); }
  FDate.now = _now; FDate.parse = OD.parse; FDate.UTC = OD.UTC; FDate.prototype = OD.prototype;
  window.Date = FDate;
  if (window.performance) performance.now = () => window.__filmT * 1000;
  const rafs = new Set(); let id = 1;
  window.requestAnimationFrame = cb => { const i = id++; rafs.add({ i, cb }); return i; };
  window.cancelAnimationFrame = i => { for (const r of rafs) if (r.i === i) { rafs.delete(r); return; } };
  window.__flushRaf = () => { const snap = [...rafs]; rafs.clear(); for (const r of snap) try { r.cb(window.__filmT * 1000); } catch (e) {} };
});

await page.goto('http://127.0.0.1:' + PORT + '/film.html', { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__ready === true, { timeout: 15000 });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(150);

const t0 = Date.now();
for (let f = 0; f < TOTAL; f++) {
  const tSec = f / FPS;
  await page.evaluate(t => { window.__filmT = t; window.__flushRaf(); }, tSec);
  await page.evaluate(() => window.__flushRaf());
  await page.screenshot({ path: join(FRAMES, `frame-${String(f).padStart(5,'0')}.png`), clip: { x:0, y:0, width:W, height:H } });
  if (f % 120 === 0) { const el=(Date.now()-t0)/1000, fps=(f+1)/el; process.stdout.write(`  frame ${f}/${TOTAL}  (${fps.toFixed(1)} fps, eta ${((TOTAL-f)/fps).toFixed(0)}s)\n`); }
}
process.stdout.write(`  done — ${TOTAL} frames in ${((Date.now()-t0)/1000).toFixed(0)}s\n`);
if (errors.length) console.log('PAGE ERRORS:', errors.slice(0,8));
await browser.close(); server.close();
