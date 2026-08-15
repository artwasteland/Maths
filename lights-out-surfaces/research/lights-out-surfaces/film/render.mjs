#!/usr/bin/env node
// render.mjs — render film.html to PNG frames with a deterministic clock.
// 166 s × 24 fps = 3984 frames. Frames removed after the encode by build.sh.
//
// The static server roots at the PARENT dir (research/lights-out-surfaces) so the
// page's `import ../engine.mjs` and `fetch ../data.json` resolve to the project's
// OWN verified engine and census file — the film cannot draw a number the engine
// does not compute. The page is loaded at /film/film.html.
import { createServer } from 'node:http';
import { readFileSync, mkdirSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';

let chromium;
try { ({ chromium } = await import('playwright')); }
catch {
  try { ({ chromium } = await import('playwright-core')); }
  catch { ({ chromium } = (await import('/opt/node22/lib/node_modules/playwright/index.js')).default); }
}

const HERE = new URL('.', import.meta.url).pathname;      // .../film/
const ROOT = resolve(HERE, '..');                          // .../lights-out-surfaces/
const FRAMES = join(HERE, 'frames');
mkdirSync(FRAMES, { recursive: true });

const FPS = 24, DUR = 166, TOTAL = FPS * DUR, W = 1920, H = 1080;

const types = { '.html':'text/html', '.woff2':'font/woff2', '.png':'image/png', '.js':'text/javascript', '.css':'text/css', '.mjs':'text/javascript', '.json':'application/json' };
const server = createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  const fp = join(ROOT, p === '/' ? '/film/film.html' : p);
  try { const body = readFileSync(fp); res.writeHead(200, { 'content-type': types[extname(fp)] || 'application/octet-stream' }); res.end(body); }
  catch { res.writeHead(404); res.end('404'); }
});
await new Promise(r => server.listen(7796, r));

let browser;
try { browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); }
catch { browser = await chromium.launch(); }
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));  // real page exceptions only; a favicon 404 is benign

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

await page.goto('http://127.0.0.1:7796/film/film.html?start=1700000000000', { waitUntil: 'load' });
await page.waitForFunction(() => window.__ready === true, undefined, { polling: 200, timeout: 15000 });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(150);

const t0 = Date.now();
for (let f = 0; f < TOTAL; f++) {
  const tSec = f / FPS;
  await page.evaluate(t => { window.__filmT = t; window.__flushRaf(); }, tSec);
  await page.evaluate(() => window.__flushRaf());
  await page.screenshot({ path: join(FRAMES, `frame-${String(f).padStart(5, '0')}.png`), clip: { x: 0, y: 0, width: W, height: H } });
  if (f % 240 === 0) { const el = (Date.now() - t0) / 1000, fps = (f + 1) / el; process.stdout.write(`  frame ${f}/${TOTAL}  (${fps.toFixed(1)} fps, eta ${((TOTAL - f) / fps).toFixed(0)}s)\n`); }
}
process.stdout.write(`  done — ${TOTAL} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
if (errors.length) { console.log('PAGE ERRORS:', errors.slice(0, 5)); process.exit(1); }
await browser.close(); server.close();
