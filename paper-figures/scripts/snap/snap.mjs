#!/usr/bin/env node
/**
 * snap — screenshot / audit / diff a web page via headless Chrome (CDP).
 * Zero npm dependencies; requires Node.js 22+ (built-in WebSocket) and local Chrome.
 */
import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const VERSION = '1.2.0';

const EXIT = {
  OK: 0,
  RUNTIME: 1,
  USAGE: 2,
  NO_CHROME: 3,
  LOAD_FAILED: 4,
  SELECTOR_NOT_FOUND: 5,
  SIZE_MISMATCH: 6,
  AUDIT_DEFECTS: 7,
  VISUAL_CHANGED: 8,
};

const LIST_CAP = 8;
const REGION_CAP = 20;
const COMPONENT_CAP = 2000;
const FAIL_KINDS = {
  broken: ['brokenImages'],
  overflow: ['overflow'],
  clipped: ['clippedText'],
  console: ['consoleErrors'],
  a11y: ['lowContrast', 'tinyText', 'missingAlt', 'smallTapTarget'],
};

let activeSession = null;

function log(msg) {
  process.stderr.write(`[snap] ${msg}\n`);
}

function usage(out = process.stdout) {
  out.write(`snap ${VERSION} - screenshot / audit / diff a web page with headless Chrome

Usage:
  node snap.mjs <url|file.html> [options]          screenshot mode
  node snap.mjs <url|file.html> --audit            audit mode, JSON report on stdout
  node snap.mjs <url|file.html> --check            baseline check mode, JSON on stdout
  node snap.mjs --diff <a.png> <b.png> [options]   pixel diff mode

Options:
  --selector <css>   capture the first element matching the CSS selector
  --clip x,y,w,h     capture a page-coordinate region
  --pad N            expand selector/clip capture region by N px (default 0)
  --full             capture the whole page
  --vw N --vh N      viewport size (default 1280x800)
  --scale N          device scale factor (default 1)
  --color-scheme <s> dark | light | auto, pin prefers-color-scheme (default auto)
  --dark             alias of --color-scheme dark
  --media <type>     emulate media type ('screen' or 'print')
  --ignore <css>     paint matched elements flat before capture (repeatable)
  --wait N           extra wait in ms after fonts and images settle
  --a11y             audit mode: also check contrast, font size, alt, tap size
  --fail-on <kinds>  audit gate: broken,overflow,clipped,console,a11y or all
  --strict           alias of --fail-on all
  --threshold N      diff mode: per-channel tolerance 0-255 (default 16)
  --align <mode>     diff mode: align sizes with top, bottom or min
  --region-gap N     diff mode: merge diff regions closer than N px (default 12)
  --check            baseline check: screenshot and compare with the baseline
  --baseline-dir <p> baseline directory (default .snap/baseline)
  --update-baseline  overwrite the baseline with this run
  --max-ratio N      baseline check: allowed diff ratio (default 0)
  -o <file>          output path (default ./snap-<timestamp>.png,
                     ./snap-diff-<timestamp>.png)

Environment:
  CHROME             full path to Chrome or Edge executable, set it when
                     browser is not installed at default locations

Exit codes: 0 ok | 1 runtime error | 2 usage | 3 chrome not found |
            4 page load failed | 5 selector not found | 6 diff size mismatch |
            7 audit gate hit | 8 baseline changed
`);
}

function parseArgs(argv) {
  const args = {
    _: [], vw: 1280, vh: 800, scale: 1, wait: 0, threshold: 16, pad: 0,
    colorScheme: 'auto', media: '', ignore: [], failOn: '', a11y: false,
    align: 'strict', regionGap: 12, maxRatio: 0, baselineDir: '.snap/baseline',
  };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    const val = () => {
      if (i + 1 >= argv.length) throw new Error(`missing value for ${t}`);
      return argv[++i];
    };
    const num = (name, min, max) => {
      const n = Number(val());
      if (!Number.isFinite(n) || n < min || n > max) throw new Error(`invalid value for ${t}`);
      args[name] = n;
    };
    const oneOf = (name, allowed) => {
      const v = val();
      if (!allowed.includes(v)) throw new Error(`invalid value for ${t}: ${v} (expected ${allowed.join(' | ')})`);
      args[name] = v;
    };
    switch (t) {
      case '-h': case '--help': args.help = true; break;
      case '--audit': args.audit = true; break;
      case '--full': args.full = true; break;
      case '--diff': args.diff = true; break;
      case '--check': args.check = true; break;
      case '--update-baseline': args.updateBaseline = true; break;
      case '--a11y': args.a11y = true; break;
      case '--strict': args.failOn = 'all'; break;
      case '--dark': args.colorScheme = 'dark'; break;
      case '--selector': args.selector = val(); break;
      case '--clip': args.clip = val(); break;
      case '--media': args.media = val(); break;
      case '--ignore': args.ignore.push(val()); break;
      case '--fail-on': args.failOn = val(); break;
      case '--baseline-dir': args.baselineDir = val(); break;
      case '--color-scheme': oneOf('colorScheme', ['dark', 'light', 'auto']); break;
      case '--align': oneOf('align', ['top', 'bottom', 'min', 'strict']); break;
      case '--pad': case '--padding': num('pad', 0, 10000); break;
      case '--vw': num('vw', 16, 20000); break;
      case '--vh': num('vh', 16, 200000); break;
      case '--scale': num('scale', 1, 8); break;
      case '--wait': num('wait', 0, 600000); break;
      case '--threshold': num('threshold', 0, 255); break;
      case '--region-gap': num('regionGap', 0, 1000); break;
      case '--max-ratio': num('maxRatio', 0, 1); break;
      case '-o': args.output = val(); break;
      default:
        if (t.startsWith('-') && t !== '-') throw new Error(`unknown option: ${t}`);
        args._.push(t);
    }
  }
  args.failKinds = parseFailKinds(args.failOn);
  return args;
}

function parseFailKinds(raw) {
  if (!raw) return null;
  const kinds = raw.split(',').map((s) => s.trim()).filter(Boolean);
  if (!kinds.length) throw new Error('--fail-on expects at least one defect kind');
  if (kinds.includes('all')) return Object.keys(FAIL_KINDS);
  const unknown = kinds.filter((k) => !FAIL_KINDS[k]);
  if (unknown.length) {
    throw new Error(`unknown defect kind for --fail-on: ${unknown.join(', ')} (expected ${Object.keys(FAIL_KINDS).join(', ')} or all)`);
  }
  return [...new Set(kinds)];
}

function resolveInput(raw) {
  if (/^https?:\/\//i.test(raw)) return raw;
  const abs = path.resolve(raw);
  if (!fs.existsSync(abs)) {
    const err = new Error(`input not found: ${raw}`);
    err.exitCode = EXIT.USAGE;
    throw err;
  }
  return pathToFileURL(abs).href;
}

class CDP {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
    this.waiters = [];
    this.ws.addEventListener('message', (ev) => this.onMessage(ev.data));
  }

  ready() {
    return new Promise((resolve, reject) => {
      this.ws.addEventListener('open', () => resolve(), { once: true });
      this.ws.addEventListener('error', () => reject(new Error('websocket connection to chrome failed')), { once: true });
    });
  }

  onMessage(raw) {
    let msg;
    try {
      msg = JSON.parse(typeof raw === 'string' ? raw : raw.toString());
    } catch {
      return;
    }
    if (msg.id !== undefined) {
      const entry = this.pending.get(msg.id);
      if (!entry) return;
      this.pending.delete(msg.id);
      clearTimeout(entry.timer);
      if (msg.error) entry.reject(new Error(`CDP ${entry.method}: ${msg.error.message}`));
      else entry.resolve(msg.result);
    } else if (msg.method) {
      const evt = { method: msg.method, params: msg.params || {}, sessionId: msg.sessionId };
      const wi = this.waiters.findIndex((w) => w.method === evt.method
        && (!w.sessionId || w.sessionId === evt.sessionId)
        && (!w.predicate || w.predicate(evt.params)));
      if (wi >= 0) {
        const w = this.waiters.splice(wi, 1)[0];
        clearTimeout(w.timer);
        w.resolve(evt);
      } else {
        this.events.push(evt);
      }
    }
  }

  send(method, params = {}, sessionId, timeoutMs = 30000) {
    const id = this.nextId++;
    const frame = { id, method, params };
    if (sessionId) frame.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      const entry = { method, resolve, reject, timer: null };
      entry.timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP ${method}: timed out after ${timeoutMs} ms`));
      }, timeoutMs);
      this.pending.set(id, entry);
      this.ws.send(JSON.stringify(frame));
    });
  }

  waitEvent(method, { sessionId, predicate, timeoutMs = 30000 } = {}) {
    const idx = this.events.findIndex((e) => e.method === method
      && (!sessionId || e.sessionId === sessionId)
      && (!predicate || predicate(e.params)));
    if (idx >= 0) return Promise.resolve(this.events.splice(idx, 1)[0]);
    return new Promise((resolve, reject) => {
      const w = { method, sessionId, predicate, resolve, timer: null };
      w.timer = setTimeout(() => {
        const i = this.waiters.indexOf(w);
        if (i >= 0) this.waiters.splice(i, 1);
        reject(new Error(`timed out waiting for ${method}`));
      }, timeoutMs);
      this.waiters.push(w);
    });
  }

  close() {
    try {
      this.ws.close();
    } catch {
      // already closed
    }
  }
}

function findChrome() {
  const candidates = [];
  if (process.env.CHROME) candidates.push(process.env.CHROME);
  if (process.env.LOCALAPPDATA) {
    candidates.push(path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'));
    candidates.push(path.join(process.env.LOCALAPPDATA, 'Microsoft', 'Edge', 'Application', 'msedge.exe'));
  }
  candidates.push(
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  );
  if (process.platform === 'darwin') {
    candidates.push(
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
      '/Applications/Chromium.app/Contents/MacOS/Chromium',
    );
  } else if (process.platform === 'linux') {
    candidates.push(
      '/usr/bin/google-chrome',
      '/usr/bin/google-chrome-stable',
      '/usr/bin/chromium',
      '/usr/bin/chromium-browser',
      '/usr/bin/microsoft-edge',
    );
  }
  for (const c of candidates) {
    try {
      if (c && fs.statSync(c).isFile()) return c;
    } catch {
      // keep probing
    }
  }
  return null;
}

async function shutdown(session) {
  if (!session) return;
  if (activeSession === session) activeSession = null;
  try {
    if (session.cdp) session.cdp.close();
  } catch {
    // best effort
  }
  await new Promise((resolve) => {
    if (!session.proc || session.proc.exitCode !== null) {
      resolve();
      return;
    }
    if (process.platform === 'win32') {
      const killer = spawn('taskkill', ['/pid', String(session.proc.pid), '/T', '/F'], { stdio: 'ignore' });
      killer.on('exit', resolve);
      killer.on('error', () => {
        try {
          session.proc.kill();
        } catch {
          // already gone
        }
        resolve();
      });
    } else {
      try {
        session.proc.kill('SIGKILL');
      } catch {
        // already gone
      }
      resolve();
    }
  });
  try {
    fs.rmSync(session.profileDir, { recursive: true, force: true });
  } catch {
    // best effort
  }
}

const handleSignal = async (sig) => {
  if (activeSession) {
    const s = activeSession;
    activeSession = null;
    await shutdown(s);
  }
  process.exit(sig === 'SIGINT' ? 130 : 143);
};
process.once('SIGINT', () => handleSignal('SIGINT'));
process.once('SIGTERM', () => handleSignal('SIGTERM'));

async function launchChrome() {
  const exe = findChrome();
  if (!exe) {
    const err = new Error('Google Chrome or Microsoft Edge not found; install one or set the CHROME environment variable');
    err.exitCode = EXIT.NO_CHROME;
    throw err;
  }
  const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), 'snap-profile-'));
  const proc = spawn(exe, [
    '--headless',
    '--hide-scrollbars',
    '--remote-debugging-port=0',
    `--user-data-dir=${profileDir}`,
    '--no-first-run',
    '--no-default-browser-check',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  try {
    const wsUrl = await new Promise((resolve, reject) => {
      let buf = '';
      const timer = setTimeout(() => reject(new Error('timeout waiting for the DevTools endpoint')), 20000);
      proc.stderr.on('data', (d) => {
        buf += d.toString();
        const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
        if (m) {
          clearTimeout(timer);
          resolve(m[1]);
        }
      });
      proc.on('exit', (code) => {
        clearTimeout(timer);
        reject(new Error(`browser exited early (code ${code})`));
      });
    });
    const cdp = new CDP(wsUrl);
    await cdp.ready();
    log('headless chrome started');
    const session = { proc, cdp, profileDir };
    activeSession = session;
    return session;
  } catch (err) {
    await shutdown({ proc, cdp: null, profileDir });
    throw err;
  }
}

async function openPage(cdp) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  await cdp.send('Page.enable', {}, sessionId);
  await cdp.send('Runtime.enable', {}, sessionId);
  await cdp.send('Log.enable', {}, sessionId);
  await cdp.send('Network.enable', {}, sessionId);
  return sessionId;
}

async function evaluate(cdp, sessionId, expression, { awaitPromise = false, timeoutMs = 30000 } = {}) {
  const res = await cdp.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true }, sessionId, timeoutMs);
  if (res.exceptionDetails) {
    const d = res.exceptionDetails;
    const detail = (d.exception && d.exception.description) || d.text || 'unknown error';
    throw new Error(`page evaluation failed: ${detail}`);
  }
  return res.result ? res.result.value : undefined;
}

const SETTLE_SCRIPT = `(async () => {
  try { await document.fonts.ready; } catch (e) { /* font API unavailable */ }
  await Promise.all(Array.from(document.images).map((img) => img.decode().catch(() => {})));
  return true;
})()`;

async function navigateAndSettle(cdp, sessionId, url, extraWaitMs) {
  const t0 = Date.now();
  await cdp.send('Page.navigate', { url }, sessionId);
  const deadline = Date.now() + 45000;
  for (;;) {
    const state = await evaluate(cdp, sessionId, '({ ready: document.readyState, href: location.href })').catch(() => null);
    if (state && state.ready === 'complete' && state.href !== 'about:blank') break;
    if (Date.now() > deadline) {
      const err = new Error(`page load failed or timed out: ${url}`);
      err.exitCode = EXIT.LOAD_FAILED;
      throw err;
    }
    await new Promise((r) => setTimeout(r, 120));
  }
  await evaluate(cdp, sessionId, SETTLE_SCRIPT, { awaitPromise: true, timeoutMs: 30000 });
  if (extraWaitMs > 0) await new Promise((r) => setTimeout(r, extraWaitMs));
  return Date.now() - t0;
}

const IGNORE_SCRIPT = (selectors) => `(() => {
  const sels = ${JSON.stringify(selectors)};
  const parse = (s) => {
    const m = String(s).match(/rgba?\\(([^)]+)\\)/);
    if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const resolveBg = (el) => {
    const stack = [];
    let node = el;
    while (node && node.nodeType === 1) {
      const cs = getComputedStyle(node);
      const c = parse(node.tagName === 'HTML' || node.tagName === 'BODY' ? (cs.backgroundColor || 'rgb(255,255,255)') : cs.backgroundColor);
      if (c && c.a > 0) {
        stack.push(c);
        if (c.a >= 1) break;
      }
      node = node.parentElement;
    }
    let base = { r: 255, g: 255, b: 255 };
    for (let i = stack.length - 1; i >= 0; i--) {
      const c = stack[i];
      base = { r: c.r * c.a + base.r * (1 - c.a), g: c.g * c.a + base.g * (1 - c.a), b: c.b * c.a + base.b * (1 - c.a) };
    }
    return 'rgb(' + Math.round(base.r) + ',' + Math.round(base.g) + ',' + Math.round(base.b) + ')';
  };
  const els = [];
  for (const s of sels) {
    try {
      for (const el of document.querySelectorAll(s)) if (!els.includes(el)) els.push(el);
    } catch (e) { /* invalid selector handled by caller */ }
  }
  for (const el of els) {
    const r = el.getBoundingClientRect();
    const cover = document.createElement('div');
    cover.setAttribute('data-snap-ignore', '');
    cover.style.cssText = [
      'position:absolute',
      'left:' + (r.left + window.scrollX) + 'px',
      'top:' + (r.top + window.scrollY) + 'px',
      'width:' + r.width + 'px',
      'height:' + r.height + 'px',
      'background:' + resolveBg(el),
      'z-index:2147483647',
      'pointer-events:none',
    ].join(';');
    el.style.visibility = 'hidden';
    document.body.appendChild(cover);
  }
  return els.length;
})()`;

async function emulate(cdp, sessionId, args) {
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: args.vw, height: args.vh, deviceScaleFactor: args.scale, mobile: false,
  }, sessionId);
  const features = [];
  if (args.colorScheme === 'dark' || args.colorScheme === 'light') {
    features.push({ name: 'prefers-color-scheme', value: args.colorScheme });
  }
  if (args.media || features.length) {
    await cdp.send('Emulation.setEmulatedMedia', { media: args.media || '', features }, sessionId);
  }
}

async function applyIgnore(cdp, sessionId, selectors) {
  if (!selectors || !selectors.length) return 0;
  const count = await evaluate(cdp, sessionId, IGNORE_SCRIPT(selectors));
  if (!count) log(`--ignore matched no element: ${selectors.join(', ')}`);
  else log(`ignored ${count} element(s): ${selectors.join(', ')}`);
  return count || 0;
}

async function preparePage(args, rawInput) {
  const url = resolveInput(rawInput);
  const session = await launchChrome();
  try {
    const sessionId = await openPage(session.cdp);
    await emulate(session.cdp, sessionId, args);
    const loadMs = await navigateAndSettle(session.cdp, sessionId, url, args.wait);
    log(`page loaded in ${loadMs} ms`);
    await applyIgnore(session.cdp, sessionId, args.ignore);
    return { session, sessionId, url, loadMs };
  } catch (err) {
    await shutdown(session);
    throw err;
  }
}


function auditScript(includeA11y) {
  return `(() => {
  const CAP = ${LIST_CAP};
  const A11Y = ${includeA11y ? 'true' : 'false'};
  const describe = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    else if (typeof el.className === 'string' && el.className.trim()) s += '.' + el.className.trim().split(/\\s+/).join('.');
    const text = (el.textContent || '').trim().replace(/\\s+/g, ' ');
    if (text) s += ' "' + (text.length > 24 ? text.slice(0, 24) + '...' : text) + '"';
    return s;
  };
  const parseColor = (s) => {
    const m = String(s).match(/rgba?\\(([^)]+)\\)/);
    if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const chan = (v) => {
    const n = v / 255;
    return n <= 0.03928 ? n / 12.92 : Math.pow((n + 0.055) / 1.055, 2.4);
  };
  const relLum = (c) => 0.2126 * chan(c.r) + 0.7152 * chan(c.g) + 0.0722 * chan(c.b);
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const bgOf = (el) => {
    const stack = [];
    let node = el;
    while (node && node.nodeType === 1) {
      const cs = getComputedStyle(node);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0) {
        stack.push(c);
        if (c.a >= 1) break;
      }
      node = node.parentElement;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };
  const hasOwnText = (el) => {
    for (const n of el.childNodes) if (n.nodeType === 3 && n.nodeValue.trim()) return true;
    return false;
  };
  const doc = document.documentElement;
  const report = {
    url: location.href,
    title: document.title,
    fontsReady: document.fonts.status === 'loaded',
    scroll: {
      clientWidth: doc.clientWidth,
      scrollWidth: doc.scrollWidth,
      clientHeight: doc.clientHeight,
      scrollHeight: doc.scrollHeight,
    },
    brokenImages: [],
    overflow: [],
    clippedText: [],
  };
  const counts = { brokenImages: 0, overflow: 0, clippedText: 0 };
  if (A11Y) {
    for (const key of ['lowContrast', 'tinyText', 'missingAlt', 'smallTapTarget']) {
      report[key] = [];
      counts[key] = 0;
    }
  }
  const push = (key, item) => {
    counts[key]++;
    if (report[key].length < CAP) report[key].push(item);
  };
  for (const img of document.images) {
    if (!img.getAttribute('src')) continue;
    if (!img.complete || img.naturalWidth === 0) {
      push('brokenImages', {
        src: img.currentSrc || img.src,
        complete: img.complete,
        naturalWidth: img.naturalWidth,
        status: 'failed',
      });
    }
  }
  const docOverflow = doc.scrollWidth > doc.clientWidth + 1;
  const all = document.body ? document.body.querySelectorAll('*') : [];
  for (const el of all) {
    const cs = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    if (docOverflow && rect.width > 0 && rect.right > doc.clientWidth + 1) {
      push('overflow', { element: describe(el), right: Math.round(rect.right), viewport: doc.clientWidth });
    }
    const cutY = el.scrollHeight - el.clientHeight;
    const cutX = el.scrollWidth - el.clientWidth;
    const hidY = cs.overflowY === 'hidden' || cs.overflowY === 'clip';
    const hidX = cs.overflowX === 'hidden' || cs.overflowX === 'clip';
    if (((hidY && cutY > 2) || (hidX && cutX > 2)) && el.textContent.trim()) {
      const to = cs.textOverflow || '';
      const lc = cs.webkitLineClamp || cs.lineClamp || '';
      if (!(to.includes('ellipsis') || (lc && lc !== 'none'))) {
        push('clippedText', { element: describe(el), overflowYpx: cutY, overflowXpx: cutX });
      }
    }
    if (!A11Y) continue;
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
    if (rect.width <= 0 || rect.height <= 0) continue;
    if (el.tagName === 'IMG' && !el.hasAttribute('alt')) {
      push('missingAlt', { src: el.currentSrc || el.src || '' });
    }
    if (el.matches('a[href],button,[role="button"],input[type="submit"],input[type="button"]')
      && (rect.width < 24 || rect.height < 24)) {
      push('smallTapTarget', {
        element: describe(el), width: Math.round(rect.width), height: Math.round(rect.height),
      });
    }
    if (!hasOwnText(el)) continue;
    const fs = parseFloat(cs.fontSize) || 0;
    if (fs > 0 && fs < 10) push('tinyText', { element: describe(el), fontSizePx: Math.round(fs * 10) / 10 });
    const fg = parseColor(cs.color);
    const bg = fg && fg.a > 0 ? bgOf(el) : null;
    if (!fg || !bg) continue;
    const solid = over(fg, bg);
    const l1 = relLum(solid);
    const l2 = relLum(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const required = (fs >= 24 || (fs >= 18.66 && weight >= 700)) ? 3 : 4.5;
    if (ratio < required - 0.01) {
      push('lowContrast', {
        element: describe(el),
        ratio: Math.round(ratio * 100) / 100,
        required,
        color: cs.color,
        background: 'rgb(' + Math.round(bg.r) + ',' + Math.round(bg.g) + ',' + Math.round(bg.b) + ')',
      });
    }
  }
  report.counts = counts;
  report.truncated = {};
  for (const key of Object.keys(counts)) report.truncated[key] = counts[key] > CAP;
  return report;
})()`;
}
function collectConsoleErrors(cdp, sessionId) {
  const errors = [];
  const seen = new Set();
  const push = (err) => {
    const key = `${err.type}|${err.text}|${err.url || ''}`;
    if (!seen.has(key)) {
      seen.add(key);
      errors.push(err);
    }
  };
  for (const evt of cdp.events) {
    if (evt.sessionId !== sessionId) continue;
    const p = evt.params;
    if (evt.method === 'Runtime.consoleAPICalled' && p.type === 'error') {
      const text = p.args.map((a) => (a.value !== undefined ? String(a.value) : a.description || '')).join(' ').trim();
      push({ type: 'console.error', text });
    } else if (evt.method === 'Runtime.exceptionThrown') {
      const d = p.exceptionDetails || {};
      push({ type: 'exception', text: (d.exception && d.exception.description) || d.text || 'unknown exception' });
    } else if (evt.method === 'Log.entryAdded' && p.entry && p.entry.level === 'error') {
      push({ type: `log.${p.entry.source}`, text: p.entry.text, url: p.entry.url });
    } else if (evt.method === 'Network.loadingFailed' && !p.canceled) {
      push({ type: 'network.failed', text: `${p.errorText} (${p.type || 'resource'})`, url: p.requestId });
    } else if (evt.method === 'Network.responseReceived' && p.response && p.response.status >= 400) {
      push({ type: 'network.http', text: `HTTP ${p.response.status} ${p.response.statusText}`, url: p.response.url });
    }
  }
  return errors;
}

function pngDimensions(buf) {
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

function parseClip(raw) {
  const parts = raw.split(',').map((s) => Number(s.trim()));
  const invalid = () => {
    const err = new Error('--clip expects x,y,w,h with numeric values, width and height must be positive');
    err.exitCode = EXIT.USAGE;
    return err;
  };
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) throw invalid();
  const [x, y, width, height] = parts;
  if (width <= 0 || height <= 0) throw invalid();
  return { x, y, width, height, scale: 1 };
}

async function resolveClip(args, cdp, sessionId) {
  if (args.full) {
    const { contentSize } = await cdp.send('Page.getLayoutMetrics', {}, sessionId);
    return {
      clip: { x: 0, y: 0, width: Math.ceil(contentSize.width), height: Math.ceil(contentSize.height), scale: 1 },
      what: 'full page',
    };
  }
  if (args.selector) {
    const rect = await evaluate(cdp, sessionId, `(() => {
      const el = document.querySelector(${JSON.stringify(args.selector)});
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width, height: r.height };
    })()`);
    if (!rect) {
      const err = new Error(`selector matched no element: ${args.selector}`);
      err.exitCode = EXIT.SELECTOR_NOT_FOUND;
      throw err;
    }
    if (rect.width <= 0 || rect.height <= 0) {
      const err = new Error(`element "${args.selector}" has zero dimensions (${rect.width}x${rect.height})`);
      err.exitCode = EXIT.SELECTOR_NOT_FOUND;
      throw err;
    }
    const pad = args.pad || 0;
    return {
      clip: {
        x: Math.max(0, rect.x - pad),
        y: Math.max(0, rect.y - pad),
        width: Math.ceil(rect.width + pad * 2),
        height: Math.ceil(rect.height + pad * 2),
        scale: 1,
      },
      what: `element "${args.selector}"${pad ? ` (pad ${pad}px)` : ''}`,
    };
  }
  if (args.clip) {
    const baseClip = parseClip(args.clip);
    const pad = args.pad || 0;
    return {
      clip: {
        x: Math.max(0, baseClip.x - pad),
        y: Math.max(0, baseClip.y - pad),
        width: Math.ceil(baseClip.width + pad * 2),
        height: Math.ceil(baseClip.height + pad * 2),
        scale: 1,
      },
      what: `region${pad ? ` (pad ${pad}px)` : ''}`,
    };
  }
  return { clip: null, what: 'viewport' };
}

async function capturePng(cdp, sessionId, clip) {
  const params = { format: 'png' };
  if (clip) {
    params.clip = clip;
    params.captureBeyondViewport = true;
  }
  const { data } = await cdp.send('Page.captureScreenshot', params, sessionId, 120000);
  return Buffer.from(data, 'base64');
}

async function runScreenshot(args, cdp, sessionId) {
  const { clip, what } = await resolveClip(args, cdp, sessionId);
  const png = await capturePng(cdp, sessionId, clip);
  const outPath = args.output || `snap-${Date.now()}.png`;
  fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
  fs.writeFileSync(outPath, png);
  const dim = pngDimensions(png);
  process.stdout.write(`[snap] saved ${outPath} (${dim.width}x${dim.height} px, ${what}, ${Math.round(png.length / 1024)} KB)\n`);
  return EXIT.OK;
}

function checkKey(args, url) {
  const signature = JSON.stringify({
    url,
    vw: args.vw,
    vh: args.vh,
    scale: args.scale,
    colorScheme: args.colorScheme,
    media: args.media,
    full: !!args.full,
    selector: args.selector || '',
    clip: args.clip || '',
    pad: args.pad,
    ignore: args.ignore,
  });
  return crypto.createHash('sha1').update(signature).digest('hex').slice(0, 12);
}

async function runCheck(args, page) {
  const dir = path.resolve(args.baselineDir);
  const key = checkKey(args, page.url);
  const baseline = path.join(dir, `${key}.png`);
  const currentPath = path.join(dir, `${key}.current.png`);
  const diffPath = path.join(dir, `${key}.diff.png`);
  const { clip } = await resolveClip(args, page.session.cdp, page.sessionId);
  const png = await capturePng(page.session.cdp, page.sessionId, clip);
  const dim = pngDimensions(png);
  fs.mkdirSync(dir, { recursive: true });
  const existed = fs.existsSync(baseline);
  if (!existed || args.updateBaseline) {
    fs.writeFileSync(baseline, png);
    const status = existed ? 'baseline-updated' : 'baseline-created';
    process.stdout.write(JSON.stringify({
      status, key, baseline, width: dim.width, height: dim.height, maxRatio: args.maxRatio,
    }, null, 2) + '\n');
    log(`baseline ${existed ? 'updated' : 'created'}: ${baseline}`);
    return EXIT.OK;
  }
  const aUrl = `data:image/png;base64,${fs.readFileSync(baseline).toString('base64')}`;
  const bUrl = `data:image/png;base64,${png.toString('base64')}`;
  const res = await evaluate(page.session.cdp, page.sessionId, diffScript(aUrl, bUrl, {
    threshold: args.threshold, align: 'strict', regionGap: args.regionGap,
  }), { awaitPromise: true, timeoutMs: 120000 });
  fs.writeFileSync(currentPath, png);
  if (!res || res.sizeMismatch) {
    process.stdout.write(JSON.stringify({
      status: 'changed',
      key,
      baseline,
      current: currentPath,
      diffImage: null,
      sizeMismatch: true,
      baselineSize: res ? res.a : null,
      currentSize: res ? res.b : [dim.width, dim.height],
      maxRatio: args.maxRatio,
    }, null, 2) + '\n');
    log('baseline size differs from the current capture');
    return EXIT.VISUAL_CHANGED;
  }
  const diffPng = Buffer.from(res.diffPng.replace(/^data:image\/png;base64,/, ''), 'base64');
  fs.writeFileSync(diffPath, diffPng);
  const ratio = Number(res.ratio.toFixed(6));
  const changed = res.ratio > args.maxRatio;
  process.stdout.write(JSON.stringify({
    status: changed ? 'changed' : 'pass',
    key,
    baseline,
    current: currentPath,
    diffImage: diffPath,
    width: res.width,
    height: res.height,
    diffPixels: res.diffPixels,
    ratio,
    maxRatio: args.maxRatio,
    regionCount: res.regionCount,
    regions: res.regions,
  }, null, 2) + '\n');
  return changed ? EXIT.VISUAL_CHANGED : EXIT.OK;
}

async function runAudit(args, session, sessionId, loadMs) {
  const report = await evaluate(session.cdp, sessionId, auditScript(args.a11y), { timeoutMs: 60000 });
  report.loadMs = loadMs;
  report.consoleErrors = collectConsoleErrors(session.cdp, sessionId);
  const failed = [];
  for (const [kind, fields] of Object.entries(FAIL_KINDS)) {
    if (fields.some((f) => Array.isArray(report[f]) && report[f].length > 0)) failed.push(kind);
  }
  const gated = Array.isArray(args.failKinds);
  const gateFailed = gated ? failed.filter((k) => args.failKinds.includes(k)) : [];
  report.verdict = { status: failed.length ? 'fail' : 'pass', failed, gated, gateFailed };
  const json = JSON.stringify(report, null, 2);
  if (args.output) {
    fs.mkdirSync(path.dirname(path.resolve(args.output)), { recursive: true });
    fs.writeFileSync(args.output, json + '\n');
    log(`audit report saved to ${args.output}`);
  }
  process.stdout.write(json + '\n');
  if (gated && gateFailed.length) {
    log(`audit gate hit: ${gateFailed.join(', ')}`);
    return EXIT.AUDIT_DEFECTS;
  }
  return EXIT.OK;
}

async function runPage(args, rawInput) {
  const page = await preparePage(args, rawInput);
  try {
    if (args.check) return await runCheck(args, page);
    if (args.audit) return await runAudit(args, page.session, page.sessionId, page.loadMs);
    return await runScreenshot(args, page.session.cdp, page.sessionId);
  } finally {
    await shutdown(page.session);
  }
}

function diffScript(aDataUrl, bDataUrl, opts) {
  const { threshold, align, regionGap } = opts;
  return `(async () => {
    const load = (src) => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('cannot decode image'));
      image.src = src;
    });
    const [a, b] = await Promise.all([load(${JSON.stringify(aDataUrl)}), load(${JSON.stringify(bDataUrl)})]);
    const mode = ${JSON.stringify(align)};
    const same = a.width === b.width && a.height === b.height;
    if (!same && mode === 'strict') {
      return { sizeMismatch: true, a: [a.width, a.height], b: [b.width, b.height] };
    }
    const W = Math.min(a.width, b.width);
    const H = Math.min(a.height, b.height);
    const ay = (!same && mode === 'bottom') ? a.height - H : 0;
    const by = (!same && mode === 'bottom') ? b.height - H : 0;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(a, 0, ay, W, H, 0, 0, W, H);
    const da = ctx.getImageData(0, 0, W, H).data;
    ctx.clearRect(0, 0, W, H);
    ctx.drawImage(b, 0, by, W, H, 0, 0, W, H);
    const db = ctx.getImageData(0, 0, W, H).data;
    const out = ctx.createImageData(W, H);
    const mask = new Uint8Array(W * H);
    let diffPixels = 0;
    let minX = Infinity, minY = Infinity, maxX = -1, maxY = -1;
    for (let i = 0; i < da.length; i += 4) {
      const d = Math.max(
        Math.abs(da[i] - db[i]),
        Math.abs(da[i + 1] - db[i + 1]),
        Math.abs(da[i + 2] - db[i + 2]),
        Math.abs(da[i + 3] - db[i + 3]),
      );
      if (d > ${threshold}) {
        diffPixels++;
        const p = i >> 2;
        mask[p] = 1;
        const x = p % W;
        const y = (p / W) | 0;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
        out.data[i] = 255;
        out.data[i + 1] = 0;
        out.data[i + 2] = 51;
        out.data[i + 3] = 255;
      } else {
        const gray = da[i] * 0.299 + da[i + 1] * 0.587 + da[i + 2] * 0.114;
        const muted = Math.round(255 * 0.55 + gray * 0.45);
        out.data[i] = muted;
        out.data[i + 1] = muted;
        out.data[i + 2] = muted;
        out.data[i + 3] = da[i + 3];
      }
    }
    const comps = [];
    if (diffPixels) {
      const stack = [];
      for (let p0 = 0; p0 < mask.length; p0++) {
        if (!mask[p0]) continue;
        mask[p0] = 0;
        stack.push(p0);
        let count = 0;
        let x0 = W, y0 = H, x1 = -1, y1 = -1;
        while (stack.length) {
          const p = stack.pop();
          count++;
          const x = p % W;
          const y = (p / W) | 0;
          if (x < x0) x0 = x;
          if (x > x1) x1 = x;
          if (y < y0) y0 = y;
          if (y > y1) y1 = y;
          if (x > 0 && mask[p - 1]) { mask[p - 1] = 0; stack.push(p - 1); }
          if (x < W - 1 && mask[p + 1]) { mask[p + 1] = 0; stack.push(p + 1); }
          if (y > 0 && mask[p - W]) { mask[p - W] = 0; stack.push(p - W); }
          if (y < H - 1 && mask[p + W]) { mask[p + W] = 0; stack.push(p + W); }
        }
        comps.push({ x0, y0, x1, y1, diffPixels: count });
      }
    }
    let seed = comps;
    if (seed.length > ${COMPONENT_CAP}) {
      seed = seed.slice().sort((m, n) => n.diffPixels - m.diffPixels).slice(0, ${COMPONENT_CAP});
    }
    const gap = ${regionGap};
    const touches = (m, n) => m.x0 - gap <= n.x1 && n.x0 - gap <= m.x1 && m.y0 - gap <= n.y1 && n.y0 - gap <= m.y1;
    let merged = seed.map((r) => ({ x0: r.x0, y0: r.y0, x1: r.x1, y1: r.y1, diffPixels: r.diffPixels }));
    for (let pass = 0; pass < 50; pass++) {
      let changed = false;
      const next = [];
      for (const r of merged) {
        let target = null;
        for (const m of next) {
          if (touches(m, r)) { target = m; break; }
        }
        if (target) {
          target.x0 = Math.min(target.x0, r.x0);
          target.y0 = Math.min(target.y0, r.y0);
          target.x1 = Math.max(target.x1, r.x1);
          target.y1 = Math.max(target.y1, r.y1);
          target.diffPixels += r.diffPixels;
          changed = true;
        } else {
          next.push({ x0: r.x0, y0: r.y0, x1: r.x1, y1: r.y1, diffPixels: r.diffPixels });
        }
      }
      merged = next;
      if (!changed) break;
    }
    merged.sort((m, n) => (m.y0 - n.y0) || (m.x0 - n.x0));
    const regionCount = merged.length;
    const regions = merged.slice(0, ${REGION_CAP}).map((r) => ({
      x0: r.x0, y0: r.y0, x1: r.x1, y1: r.y1,
      width: r.x1 - r.x0 + 1, height: r.y1 - r.y0 + 1, diffPixels: r.diffPixels,
    }));
    ctx.putImageData(out, 0, 0);
    return {
      width: W,
      height: H,
      totalPixels: W * H,
      diffPixels,
      ratio: diffPixels / (W * H),
      bbox: diffPixels ? { x0: minX, y0: minY, x1: maxX, y1: maxY } : null,
      regions,
      regionCount,
      aligned: same ? null : {
        mode, a: [a.width, a.height], b: [b.width, b.height], width: W, height: H, cropped: true,
      },
      diffPng: canvas.toDataURL('image/png'),
    };
  })()`;
}

async function runDiff(args) {
  if (args._.length !== 2) {
    usage(process.stderr);
    return EXIT.USAGE;
  }
  const [pa, pb] = args._.map((p) => {
    const abs = path.resolve(p);
    if (!fs.existsSync(abs)) {
      const err = new Error(`input not found: ${p}`);
      err.exitCode = EXIT.USAGE;
      throw err;
    }
    return abs;
  });
  const dataUrls = [pa, pb].map((p) => `data:image/png;base64,${fs.readFileSync(p).toString('base64')}`);
  const session = await launchChrome();
  try {
    const sessionId = await openPage(session.cdp);
    const res = await evaluate(session.cdp, sessionId, diffScript(dataUrls[0], dataUrls[1], {
      threshold: args.threshold, align: args.align, regionGap: args.regionGap,
    }), {
      awaitPromise: true,
      timeoutMs: 120000,
    });
    if (!res || res.sizeMismatch) {
      const info = res ? ` (a: ${res.a[0]}x${res.a[1]}, b: ${res.b[0]}x${res.b[1]})` : '';
      const err = new Error(`image sizes differ${info}; diff refused, use --align top|bottom|min to compare a common area`);
      err.exitCode = EXIT.SIZE_MISMATCH;
      throw err;
    }
    const outPath = args.output || `snap-diff-${Date.now()}.png`;
    const png = Buffer.from(res.diffPng.replace(/^data:image\/png;base64,/, ''), 'base64');
    fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
    fs.writeFileSync(outPath, png);
    const summary = {
      a: path.basename(pa),
      b: path.basename(pb),
      width: res.width,
      height: res.height,
      totalPixels: res.totalPixels,
      diffPixels: res.diffPixels,
      ratio: Number(res.ratio.toFixed(6)),
      bbox: res.bbox,
      regions: res.regions,
      regionCount: res.regionCount,
      aligned: res.aligned,
      diffImage: outPath,
    };
    process.stdout.write(JSON.stringify(summary, null, 2) + '\n');
    return EXIT.OK;
  } finally {
    await shutdown(session);
  }
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (err) {
    process.stderr.write(`[snap] ${err.message}\n`);
    usage(process.stderr);
    return EXIT.USAGE;
  }
  if (args.help) {
    usage();
    return EXIT.OK;
  }
  try {
    if (args.diff) return await runDiff(args);
    if (args._.length !== 1) {
      usage(process.stderr);
      return EXIT.USAGE;
    }
    return await runPage(args, args._[0]);
  } catch (err) {
    log(`error: ${err.message}`);
    return err.exitCode || EXIT.RUNTIME;
  }
}

process.exitCode = await main();
