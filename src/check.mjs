// Checks the profile README (../README.md, images in ../assets/) in headless Chrome and saves
// screenshots of the preview frames to shots/.
//
// Run: node check.mjs   (Node 22+, Google Chrome in /Applications or at $CHROME, gh CLI signed in,
//                        xmllint; run build_preview.py first. ./build.sh --check runs both.)
// Optional local files, gitignored under local/ (the compare shots that need them are skipped
// when they are missing):
//   local/seti-ref/        the official SETI reference photos (cards/, web/)
//   local/page-v3/assets/  the first card design
//   local/page-v9/assets/  the earlier flat-edged poster pile (card-back-poster-*.svg)
// 0. Static checks on the files: every SVG passes xmllint, stays under SIZE_MAX, holds no script,
//    foreignObject, text element, event-handler attribute, external URL or font, and every
//    animated SVG carries the prefers-reduced-motion rule. Raster images are allowed only as
//    embedded data: URIs (png, webp, jpeg), and not in About. The generators in gen/ and the
//    scripts here hold no absolute macOS home paths (HOME_PATH).
// 1. Preview frames (index.html): text sizes, three cards on one row, header alignment,
//    no sideways scroll, no markdown headings, the easter egg's <summary> on one line with its image
//    on the text baseline (where the disclosure triangle sits). Screenshots go to shots/<frame>.png (2x).
// 2. Real README markup (gh api markdown, with every <source> kept) in a page that sizes the README
//    like GitHub does. GitHub must wrap each <picture> in <themed-picture>, and the page runs a copy of
//    that element's source rewrite (THEMED_PICTURE) for data-color-mode auto, light and dark. At window
//    widths 1280, 375, 1011.5 and 1279.5, OS theme light and dark, in each mode: each phone/desktop
//    picture pair shows exactly one image, the expected file for that width and theme (img.currentSrc);
//    every blank.svg image is 0x0 and shares its line with a shown image, so it adds no height; the
//    card back shows from 1280 px only. The fractional widths (page zoom or display scaling) sit between
//    two whole-pixel gates; the page loads in an iframe under CSS zoom 2 to get them (loadFramed). GitHub must keep the summary's <picture>s inside <summary>; a click on the
//    summary opens the details and shows the reveal image, a second click closes it.
// 3. Motion: each card SVG, shown through <img> as GitHub does, must look different in two
//    screenshots taken 1 s apart, and identical under prefers-reduced-motion: reduce.
// 4. Mirror symmetry of the device icons: each effect token of the idevice-control cards (ids
//    fx0..fx2) is rendered alone at 8x and compared with its mirror image. The TV's play mark
//    (class pm) is left out; the generator asserts it is top/bottom symmetric.
// 5. Side-by-side shots with the SETI reference photos (local/seti-ref): shots/compare-front.png
//    and shots/compare-back.png. The references appear only in these review shots, never in assets/.
//    shots/compare-first-design.png: the first card design (local/page-v3/assets) next to the
//    current wide cards, light and dark, both at 1 SVG unit = 1 CSS px, plus their title areas at
//    one zoom.
//    shots/pile-compare.png: the reference draw-pile photo, the earlier flat-edged poster pile
//    (local/page-v9/assets/card-back-poster-*.svg) and the current pile, all 403 px tall, on a light
//    and a dark page, plus their bottom-left corners at one zoom.
//    Each of these shots is skipped, with a "skip" line, when a local folder it needs is missing.
// 6. shots/title-fonts.png: the title band of both cards in each title-font candidate
//    (python3 gen/cards/build_cards.py --title-fonts writes the review SVGs to a temp folder).
// 7. Geometry, each SVG inlined in a page: on every card front the repo name (class nm) starts
//    TITLE_GAP right of the gold diamond's tip and ends at least TITLE_MARGIN inside the card, within
//    the band (class band); each heading tag's label (class lb) has the expected cap height, sits
//    vertically centred and inside its box (class box), and the chip's left edge sits at x=0; each
//    easter-egg image's text (class tx) lies inside its viewBox.
// 8. shots/details-open.png: the easter egg opened in all four preview frames (light and dark,
//    desktop and phone), the rest of the README hidden; the reveal image's text size is checked there.
import { spawn, execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, writeFileSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');
const ASSETS = path.join(ROOT, 'assets');
const LOCAL = path.join(HERE, 'local');
const REF = path.join(LOCAL, 'seti-ref');
const V9_DIR = path.join(LOCAL, 'page-v9', 'assets');
const FIRST_DIR = path.join(LOCAL, 'page-v3', 'assets');
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SIZE_MAX = 150 * 1024;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Text sizes in each SVG, in viewBox units (= px when the SVG renders at its viewBox width).
// Values come from gen/about/build.py, gen/headings.py (Oxanium SemiBold, font size = cap height /
// Oxanium's cap height 0.69: cap 10.5 px wide, 28/3 px on phones), gen/egg/build.py (Jost at the
// About body size) and gen/cards/build_cards.py (LAYOUT, TITLE_SIZE: the repo name is in Oxanium
// Bold, 18 px wide, 20 px on phones; it must render at 18 px or more).
const HEAD_CAP = { wide: 10.5, phone: 28 / 3 };
const OX = (cap) => cap / 0.69;
const TEXT = {
  'about': { body: 15 }, 'about-phone': { body: 14 },
  'h-about': { label: OX(HEAD_CAP.wide) }, 'h-project': { label: OX(HEAD_CAP.wide) },
  'h-about-phone': { label: OX(HEAD_CAP.phone) }, 'h-project-phone': { label: OX(HEAD_CAP.phone) },
  'egg-summary': { text: 15 }, 'egg-reveal': { text: 15 }, 'egg-summary-phone': { text: 14 }, 'egg-reveal-phone': { text: 14 },
  'card-idevice-control': { name: 18, line: 16 },
  'card-cc-session-breakdown': { name: 18, line: 16 },
  'card-idevice-control-phone': { name: 20, line: 15 },
  'card-cc-session-breakdown-phone': { name: 20, line: 15 },
};
// Repo name on the card fronts (gen/cards/build_cards.py TITLE_GAP, TITLE_MARGIN): horizontal gap from
// the gold diamond's right tip (outline included) to the name's ink, and the least room from the
// name's ink to the card's right edge.
const TITLE_GAP = { wide: 11, phone: 12 };
const TITLE_MARGIN = 7;
// Decorative micro text on the cards (flavour line, rotated card code), exempt from the minimums; reported only.
const MICRO = {
  'card-idevice-control': { flavour: 10.5, code: 6.6 }, 'card-cc-session-breakdown': { flavour: 10.5, code: 6.6 },
  'card-idevice-control-phone': { flavour: 10.5, code: 6.4 }, 'card-cc-session-breakdown-phone': { flavour: 10.5, code: 6.4 },
};
const stem = (src) => path.basename(src).replace(/-(light|dark)\.svg$/, '');
const svgFiles = readdirSync(ASSETS).filter((f) => f.endsWith('.svg')).sort();
const viewBoxW = {};
for (const f of svgFiles) {
  const m = readFileSync(path.join(ASSETS, f), 'utf8').match(/viewBox="[-\d.]+ [-\d.]+ ([\d.]+)/);
  viewBoxW[f] = m ? +m[1] : null;
}

const fails = [];
const check = (ok, msg) => { console.log((ok ? 'ok   ' : 'FAIL ') + msg); if (!ok) fails.push(msg); };

// ---- 0. static checks
console.log('[files]');
const FORBIDDEN = [
  [/<script/i, 'script'], [/<foreignObject/i, 'foreignObject'], [/<(text|tspan)[\s>]/i, 'text element'],
  [/\son[a-z]+\s*=/i, 'event handler'], [/@import|@font-face/i, 'external font or style'],
  [/url\(\s*['"]?(?!#)/i, 'external url()'], [/(?:xlink:)?href\s*=\s*"(?!#|data:image\/)/i, 'external href'],
  [/https?:\/\/(?!www\.w3\.org\/)/i, 'external URL'], [/\/Users\//, 'absolute home path'],
  [/<(iframe|embed|object)[\s>]/i, 'embedded object'],
];
// About, the heading tags, the easter egg and blank.svg are pure vector drawings. Cards and the header
// may embed raster images, but only as data: URIs (the external-href rule above already rejects anything else).
const VECTOR_ONLY = /^(about|blank|h-|egg-)/;
const DATA_IMAGE = /^data:image\/(png|webp|jpeg);base64,/;
const sizes = [];
for (const f of svgFiles) {
  const file = path.join(ASSETS, f);
  const src = readFileSync(file, 'utf8');
  let lint = true;
  try { execFileSync('xmllint', ['--noout', file], { stdio: 'pipe' }); } catch { lint = false; }
  const bad = FORBIDDEN.filter(([re]) => re.test(src)).map(([, name]) => name);
  if (VECTOR_ONLY.test(f) && /<image[\s>]/i.test(src)) bad.push('raster image');
  for (const m of src.matchAll(/<image\b[^>]*?\shref="([^"]*)"/gi)) if (!DATA_IMAGE.test(m[1])) bad.push('image not a data: URI');
  const size = statSync(file).size;
  const animated = /animation\s*:/.test(src);
  const reduce = /@media \(prefers-reduced-motion: reduce\) \{ \* \{ animation: none !important; \} \}/.test(src);
  sizes.push(`${f} ${(size / 1024).toFixed(1)} KB`);
  check(lint && !bad.length && size <= SIZE_MAX && (!animated || reduce),
    `${f}: xmllint ${lint ? 'ok' : 'FAILED'}, ${(size / 1024).toFixed(1)} KB, forbidden: ${bad.join(', ') || 'none'}` +
    `${animated ? ', reduced-motion rule ' + (reduce ? 'present' : 'MISSING') : ''}`);
  if (/^card-(?!back)/.test(f)) check(!/<animate|<set[\s>]/.test(src), `${f}: CSS motion only (no SMIL)`);
}
const genFiles = execFileSync('find', [path.join(HERE, 'gen'), '-type', 'f', '(', '-name', '*.py', '-o', '-name', '*.mjs', '-o', '-name', '*.js', ')']).toString().trim().split('\n');
const HOME_PATH = /\/Users\//;
const genHits = genFiles.filter((g) => HOME_PATH.test(readFileSync(g, 'utf8')));
check(genHits.length === 0, `gen/: no absolute home paths in ${genFiles.length} generator files${genHits.length ? ' (' + genHits.join(', ') + ')' : ''}`);
for (const s of ['build_preview.py', 'check.mjs', 'build.sh']) check(!HOME_PATH.test(readFileSync(path.join(HERE, s), 'utf8')), `${s}: no absolute home paths`);

async function chrome(port, extra = []) {
  const dir = mkdtempSync(path.join(tmpdir(), 'check-'));
  const proc = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', ...extra,
    `--remote-debugging-port=${port}`, `--user-data-dir=${dir}`, 'about:blank'], { stdio: 'ignore' });
  let t;
  for (let i = 0; i < 100 && !t; i++) {
    try { t = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((x) => x.type === 'page'); } catch {}
    await sleep(100);
  }
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));
  let id = 0; const pending = new Map(); const waiters = [];
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
    else if (m.method) for (const w of waiters.splice(0)) (w.method === m.method ? w.res(m.params) : waiters.push(w));
  });
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  await send('Page.enable');
  let ctx, frameDir;   // ctx: the execution context eval() runs in; undefined = the top page
  const media = (scheme, motion) => send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }, { name: 'prefers-reduced-motion', value: motion }] });
  const navigate = async (url) => {
    const loaded = new Promise((res) => waiters.push({ method: 'Page.loadEventFired', res }));
    await send('Page.navigate', { url });
    await loaded; await sleep(400);
  };
  return {
    async load(url, width, scheme, dpr = 1, motion = 'reduce', height = 900) {
      ctx = undefined;
      await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: dpr, mobile: false });
      await media(scheme, motion);
      await navigate(url);
    },
    // Loads url in an iframe `width` CSS px wide under CSS zoom 2. Chrome hands an iframe's zoom to its
    // document as page zoom, so the framed page's viewport is exactly `width` CSS px, fractions included
    // (2 x width must be a whole number). Later eval() calls run in the framed document.
    async loadFramed(url, width, scheme, motion = 'reduce', height = 900) {
      ctx = undefined;
      frameDir ??= mkdtempSync(path.join(tmpdir(), 'frame-'));
      const wrap = path.join(frameDir, 'frame.html');
      writeFileSync(wrap, `<!doctype html><html><body style="margin:0"><iframe src="${url}" style="zoom:2;display:block;border:0;width:${width}px;height:${height}px"></iframe></body></html>`);
      await send('Emulation.setDeviceMetricsOverride', { width: Math.ceil(width * 2) + 40, height: height * 2 + 40, deviceScaleFactor: 1, mobile: false });
      await media(scheme, motion);
      await navigate('file://' + wrap);
      const frameId = (await send('Page.getFrameTree')).frameTree.childFrames[0].frame.id;
      ctx = (await send('Page.createIsolatedWorld', { frameId, worldName: 'check' })).executionContextId;
    },
    async eval(expr) {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true, ...(ctx ? { contextId: ctx } : {}) });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result.value;
    },
    async shot(file, clip) {
      const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { ...clip, scale: 1 } });
      if (file) writeFileSync(file, Buffer.from(r.data, 'base64'));
      return r.data;
    },
    close() { try { send('Browser.close'); } catch {} setTimeout(() => proc.kill(), 300); },
  };
}

// The <summary> of the easter egg: its height must be one line, and the shown image's bottom edge must
// sit on the text baseline (a zero-size inline-block probe marks it), where the disclosure triangle sits.
// The summary holds a phone and a desktop picture; the widest image is the one shown.
const summaryLine = `((s) => {
  const q = s.getBoundingClientRect();
  const el = [...s.querySelectorAll('img')].sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width)[0];
  const img = el.getBoundingClientRect();
  const probe = document.createElement('span'); probe.style.cssText = 'display:inline-block;width:0;height:0';
  s.append(probe); const base = probe.getBoundingClientRect().bottom; probe.remove();
  return { h: q.height, lh: parseFloat(getComputedStyle(s).lineHeight), img: el.currentSrc.split('/').pop(),
    imgH: img.height, off: img.bottom - base };
})`;
const summaryOk = (m) => m.h <= m.lh + 0.5 && Math.abs(m.off) <= 0.5;
const summaryMsg = (m) => `${m.img} ${m.imgH}px tall in a ${m.h}px line (line-height ${m.lh}px), image bottom ${m.off.toFixed(2)}px from the baseline`;

const b = await chrome(9341);

// ---- 1. preview frames
console.log('\n[preview frames]');
await b.load('file://' + path.join(HERE, 'index.html'), 1900, 'light', 2);
mkdirSync(path.join(HERE, 'shots'), { recursive: true });
for (const frame of ['desktop-light', 'desktop-dark', 'phone-light', 'phone-dark']) {
  const r = await b.eval(`(() => {
    const summaryLine = ${summaryLine};
    const sec = document.getElementById('${frame}'), md = sec.querySelector('.markdown-body');
    const cs = getComputedStyle(md), cw = md.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const box = (e) => { const q = e.getBoundingClientRect(); return { x: q.x, y: q.y, w: q.width, h: q.height, r: q.right }; };
    const imgs = [...md.querySelectorAll('img')].filter((i) => i.checkVisibility()).map((i) => ({ src: i.getAttribute('src'), ...box(i) }));
    const s = sec.getBoundingClientRect();
    return { cw, imgs, mdLeft: md.getBoundingClientRect().x + parseFloat(cs.paddingLeft),
      scrollW: md.scrollWidth, clientW: md.clientWidth, frameScroll: sec.querySelector('.frame').scrollWidth - sec.querySelector('.frame').clientWidth,
      headings: md.querySelectorAll('h1,h2,h3,h4,h5,h6,a.anchor').length, summary: summaryLine(md.querySelector('summary')),
      clip: { x: s.x + window.scrollX, y: s.y + window.scrollY, width: s.width, height: s.height } };
  })()`);
  console.log(`\n[${frame}] README width ${r.cw}px`);
  for (const im of r.imgs) {
    const file = path.basename(im.src), t = TEXT[stem(file)];
    if (!t || im.w === 0) continue;
    const scale = im.w / viewBoxW[file];
    const sizes_ = Object.entries(t).map(([k, v]) => `${k} ${(v * scale).toFixed(1)}px`).join(', ');
    const min = Math.min(...Object.values(t)) * scale;
    const isPhone = frame.startsWith('phone'), kind = stem(file);
    let rule = '';
    if (kind === 'about') rule = min >= 14 && min <= 15 ? 'ok' : 'want 14-15';
    else if (kind === 'about-phone') rule = min >= 13 ? 'ok' : 'want >=13';
    else if (kind.startsWith('card') && isPhone) rule = min >= 11 && t.name * scale >= 18 ? 'ok' : 'want >=11, name >=18';
    else if (kind.startsWith('card')) rule = t.line * scale >= 14 && t.name * scale >= 18 ? 'ok' : 'want line >=14, name >=18';
    else if (kind.startsWith('h-')) rule = min >= 13 ? 'ok' : 'want >=13';
    else if (kind.startsWith('egg-')) rule = Math.abs(min - (isPhone ? 14 : 15)) < 0.05 ? 'ok' : 'want the About size, 15 (phone 14)';
    if (MICRO[kind]) console.log(`  ${file}: micro text ${Object.entries(MICRO[kind]).map(([k, v]) => `${k} ${(v * scale).toFixed(1)}px`).join(', ')} (exempt)`);
    console.log(`  ${file}: rendered ${im.w.toFixed(1)}x${im.h.toFixed(1)}  ${sizes_}${rule ? '  [' + rule + ']' : ''}`);
    if (rule) check(rule === 'ok', `${frame} ${file} text ${sizes_} ${rule}`);
  }
  check(r.headings === 0, `${frame}: no markdown headings or anchor links (${r.headings})`);
  check(summaryOk(r.summary), `${frame}: easter-egg summary ${summaryMsg(r.summary)}`);
  check(r.scrollW <= r.clientW && r.frameScroll <= 0, `${frame}: no sideways scroll (scrollWidth ${r.scrollW} <= clientWidth ${r.clientW})`);
  const over = r.imgs.filter((i) => i.r > r.mdLeft + r.cw + 0.5);
  check(over.length === 0, `${frame}: every image inside the README width`);
  const cards = r.imgs.filter((i) => /card-|blank/.test(i.src) && i.w > 0);
  const header = r.imgs.find((i) => i.src.endsWith('header.svg'));
  if (frame.startsWith('desktop')) {
    const sameRow = cards.length === 3 && cards.every((c) => Math.abs(c.y - cards[0].y) < 0.5);
    check(sameRow, `${frame}: three cards on one row (${cards.map((c) => path.basename(c.src)).join(', ')})`);
    const dl = cards[0].x - header.x, dr = header.r - cards[cards.length - 1].r;
    check(Math.abs(dl) <= 4 && Math.abs(dr) <= 4, `${frame}: row edges vs header edges: left ${dl.toFixed(2)}px, right ${dr.toFixed(2)}px`);
  } else {
    check(cards.every((c) => Math.abs(c.w - r.cw) < 0.5), `${frame}: phone cards fill the README width (${cards.map((c) => c.w.toFixed(1)).join(', ')})`);
  }
  await b.shot(path.join(HERE, 'shots', frame + '.png'), r.clip);
}

// ---- 2. real README markup
const body = execFileSync('gh', ['api', 'markdown', '-f', 'text=' + readFileSync(path.join(ROOT, 'README.md'), 'utf8'),
  '-f', 'mode=gfm', '-f', 'context=McDyZzz/McDyZzz']).toString();
// GitHub's <themed-picture> element (github.com JS chunk "lazy-element-themed-picture"), copied as a page
// script; the page's ?mode= sets <html data-color-mode>. With "light" or "dark" (a signed-in viewer's
// explicit theme), in each picture that has a <source> whose media holds "prefers-color-scheme", every
// <source> is sorted by its media text: "prefers-color-scheme: light" -> light, else
// "prefers-color-scheme: dark" -> dark, else left alone. Sources of the active theme get a media that
// always matches, the other theme's get "not all", so any other condition in the same media is lost.
// "auto" leaves every picture alone.
const THEMED_PICTURE = `<script>
const mode = new URLSearchParams(location.search).get('mode') || 'auto';
document.documentElement.setAttribute('data-color-mode', mode);
for (const t of document.querySelectorAll('themed-picture')) {
  const sources = [...t.firstElementChild.querySelectorAll('source')];
  if (mode === 'auto' || !sources.some((s) => (s.getAttribute('media') ?? '').includes('prefers-color-scheme'))) continue;
  for (const s of sources) {
    const media = s.getAttribute('media') ?? '';
    // As in GitHub's code, String.match turns the string into a RegExp: the parentheses form a group,
    // so this is a substring test for the text inside them.
    const theme = media.match('(prefers-color-scheme: light)') ? 'light' : media.match('(prefers-color-scheme: dark)') ? 'dark' : null;
    if (theme) s.setAttribute('media', theme === mode ? '(prefers-color-scheme: light),(prefers-color-scheme: dark)' : 'not all');
  }
}
</script>`;
// README width as on github.com/<user>: 846 px from 1280 px up; window - 434 from 1012; window - 370 from 768; window - 82 below.
const real = `<!doctype html><html><head><meta charset="utf-8"><base href="file://${ROOT}/"><style>
body{margin:0;font:16px/1.5 sans-serif} .markdown-body{margin:0 auto;width:calc(100vw - 82px)}
@media (min-width:768px){.markdown-body{width:calc(100vw - 370px)}} @media (min-width:1012px){.markdown-body{width:calc(100vw - 434px)}}
@media (min-width:1280px){.markdown-body{width:846px}}
.markdown-body p{margin:0 0 16px} .markdown-body img{max-width:100%;box-sizing:content-box}
</style></head><body><article class="markdown-body">${body}</article>${THEMED_PICTURE}</body></html>`;
const realFile = path.join(mkdtempSync(path.join(tmpdir(), 'real-')), 'real.html');
writeFileSync(realFile, real);
// The file each picture pair (keyed by the start of its alt text) must show; null: no image. Every
// themed image is a phone picture plus a desktop picture; the card back (alt "") is one picture.
const expect = (w, theme) => {
  const narrow = w < 1012 ? '-phone' : '';
  return {
    'About': `h-about${narrow}-${theme}.svg`,
    'I build': `about${narrow}-${theme}.svg`,
    'Featured projects': `h-project${narrow}-${theme}.svg`,
    'idevice-control': `card-idevice-control${narrow}-${theme}.svg`,
    'cc-session-breakdown': `card-cc-session-breakdown${narrow}-${theme}.svg`,
    '': w >= 1280 ? `card-back-${theme}.svg` : null,
    "Don't click this.": `egg-summary${narrow}-${theme}.svg`,
    'I taught Claude': `egg-reveal${narrow}-${theme}.svg`,
  };
};
console.log('\n[real README markup]');
const pictures = (body.match(/<picture>/g) || []).length;
const themed = (body.match(/<themed-picture[\s>][^]*?<\/themed-picture>/g) || []).filter((t) => /^<themed-picture[^>]*><picture>[^]*<\/picture><\/themed-picture>$/.test(t)).length;
check(pictures === 15 && themed === pictures, `GitHub wraps each of the ${pictures} <picture>s in its own <themed-picture> (${themed})`);
const details = (body.match(/<details>[\s\S]*?<\/details>/) || [''])[0];
const summaryHtml = (details.match(/<summary>[\s\S]*?<\/summary>/) || [''])[0];
check(/<picture>[\s\S]*<img [^>]*alt="Don't click this\."[^>]*>[\s\S]*<\/picture>/.test(summaryHtml) && !/<a[\s>]/.test(summaryHtml),
  `GitHub keeps the summary's <picture>s inside <summary>, with no link around the images: ${summaryHtml.replace(/<source[^>]*>/g, '').slice(0, 160)}`);
check(/<\/summary>[\s\S]*<picture>[\s\S]*alt="I taught Claude to tap my iPhone\. Then it wanted the Apple TV remote\. Now it reads my token bills\."/.test(details),
  'the reveal <picture>s follow the summary inside <details>, alt text holds the three lines');
const links = (body.match(/<a href="[^"]+"/g) || []).map((a) => a.slice(9, -1));
check(links.includes('https://github.com/McDyZzz/idevice-control') && links.includes('https://github.com/McDyZzz/cc-session-breakdown'),
  `card links: ${links.filter((l) => /McDyZzz\//.test(l)).join(', ')}`);
for (const w of [1280, 375, 1011.5, 1279.5, 1100, 900]) {
  const frac = w % 1 !== 0, checked = w === 1280 || w === 375 || frac;
  for (const scheme of ['light', 'dark']) {
    for (const mode of checked ? ['auto', 'light', 'dark'] : ['auto']) {
      const url = 'file://' + realFile + '?mode=' + mode;
      await (frac ? b.loadFramed(url, w, scheme) : b.load(url, w, scheme));
      const theme = mode === 'auto' ? scheme : mode, label = `window ${w} OS ${scheme} mode ${mode}`;
      // A fractional width must be the exact CSS viewport, between the whole-pixel gates below and above it.
      const vp = frac ? await b.eval(`({ iw: innerWidth, exact: matchMedia('(min-width: ${w - 0.01}px) and (max-width: ${w + 0.01}px)').matches,
        gap: !matchMedia('(max-width: ${Math.floor(w)}px)').matches && !matchMedia('(min-width: ${Math.ceil(w)}px)').matches })`) : null;
      if (checked) {
        const egg = await b.eval(`(async () => {
          const summaryLine = ${summaryLine};
          const d = document.querySelector('details'), s = d.querySelector('summary');
          const rev = [...d.querySelectorAll('img')].find((i) => !s.contains(i) && !i.currentSrc.endsWith('/blank.svg'));
          // Chrome hides closed details content with content-visibility, which keeps its layout boxes:
          // checkVisibility() tells whether the image is shown.
          const line = summaryLine(s), shut = rev.checkVisibility();
          s.click(); await new Promise((r) => setTimeout(r, 200));
          const open = d.open, shown = rev.checkVisibility() && rev.getBoundingClientRect().width;
          s.click(); await new Promise((r) => setTimeout(r, 200));
          return { line, shut, open, shown, closed: !d.open && !rev.checkVisibility() };
        })()`);
        check(summaryOk(egg.line), `${label}: summary ${summaryMsg(egg.line)}`);
        check(!egg.shut && egg.open && egg.shown > 0 && egg.closed,
          `${label}: reveal image hidden (${!egg.shut}), shown ${egg.shown}px wide after a click, hidden again after a second click (${egg.closed})`);
      }
      // With the details open, so the reveal pair is laid out as shown. onLine: another image in the
      // same block (p, summary or details) is shown and has the same bottom edge, so both sit on one line.
      const r = await b.eval(`(() => {
        document.querySelector('details').open = true;
        const imgs = [...document.querySelectorAll('picture img')], block = (i) => i.closest('summary, p, details');
        const head = document.querySelector('img[src$="header.svg"]').getBoundingClientRect();
        return { header: [head.x, head.right], imgs: imgs.map((i) => { const q = i.getBoundingClientRect();
          return { alt: i.alt, file: i.currentSrc.split('/').pop(), x: q.x, r: q.right, y: q.y, w: q.width, h: q.height,
            onLine: imgs.some((j) => { const o = j.getBoundingClientRect(); return j !== i && block(j) === block(i) && o.width > 0 && Math.abs(o.bottom - q.bottom) <= 0.5; }) }; }) };
      })()`);
      const exp = expect(w, theme), groups = {};
      for (const g of r.imgs) (groups[Object.keys(exp).find((k) => k ? g.alt.startsWith(k) : g.alt === '')] ??= []).push(g);
      const bad = Object.keys(groups).filter((k) => !(k in exp)).map((k) => `unexpected alt ${k}`);
      for (const [key, file] of Object.entries(exp)) {
        const imgs = groups[key] || [], shown = imgs.filter((i) => i.w > 0 && i.h > 0);
        const ok = imgs.length === (key ? 2 : 1) && (file ? shown.length === 1 && shown[0].file === file : shown.length === 0) &&
          imgs.every((i) => shown.includes(i) || (i.file === 'blank.svg' && i.w === 0 && i.h === 0 && i.onLine));
        if (!ok) bad.push(`${key || 'card back'}: ${imgs.map((i) => `${i.file} ${i.w}x${i.h}${i.w || i.onLine ? '' : ' on its own line'}`).join(' + ')}`);
      }
      const cards = r.imgs.filter((g) => (/^(idevice|cc-session)/.test(g.alt) || g.alt === '') && g.w > 0);
      const rows = new Set(cards.map((g) => Math.round(g.y))).size;
      const dl = cards[0].x - r.header[0], dr = r.header[1] - cards[cards.length - 1].r;
      const scroll = await b.eval('document.documentElement.scrollWidth - document.documentElement.clientWidth');
      if (vp && !(vp.exact && vp.gap)) bad.push(`CSS viewport is not ${w}px between the ${Math.floor(w)} and ${Math.ceil(w)} px gates (innerWidth ${vp.iw})`);
      const msg = `${label}${vp ? ` (CSS viewport ${w}px, innerWidth ${vp.iw})` : ''}: ${r.imgs.length} pictures, ${bad.length ? 'WRONG ' + bad.join('; ') : 'each pair shows one image, the expected file, and its blank.svg is 0x0 on the same line'}; ` +
        `cards on ${rows} row(s)${w === 1280 ? `, row edges vs header: left ${dl.toFixed(2)}px, right ${dr.toFixed(2)}px` : ''}; sideways overflow ${scroll}px`;
      if (checked) check(bad.length === 0 && scroll <= 0 && (w === 1280 ? rows === 1 && Math.abs(dl) <= 4 && Math.abs(dr) <= 4 : true), msg);
      else console.log('info ' + msg);
    }
  }
}

// ---- 3. motion
// All cards sit in one grid inside the viewport (Chrome pauses SVG image animation off screen).
// Reduced motion is set with Chrome's --force-prefers-reduced-motion switch: the DevTools media
// emulation does not reach the documents of SVG images.
console.log('\n[motion]');
const cardFiles = svgFiles.filter((f) => /^card-.*\.svg$/.test(f));
const motionPage = path.join(mkdtempSync(path.join(tmpdir(), 'motion-')), 'motion.html');
writeFileSync(motionPage, `<!doctype html><html><body style="margin:0;background:#888;display:flex;flex-wrap:wrap;gap:4px;width:1200px">${cardFiles.map((f) =>
  `<img id="${f}" src="file://${ASSETS}/${f}" style="width:293px">`).join('')}</body></html>`);
async function motionCheck(br, reduce) {
  await br.load('file://' + motionPage, 1200, 'light', 1, 'no-preference', 1300);
  await sleep(1500);
  const boxes = await br.eval(`[...document.images].map((i) => { const q = i.getBoundingClientRect(); return [i.id, q.x, q.y, q.width, q.height]; })`);
  const first = {};
  for (const [id, x, y, w, h] of boxes) first[id] = await br.shot(null, { x, y, width: w, height: h });
  await sleep(1000);
  for (const [id, x, y, w, h] of boxes) {
    const moved = (await br.shot(null, { x, y, width: w, height: h })) !== first[id];
    if (reduce) check(!moved, `${id}: still under prefers-reduced-motion`);
    else check(moved, `${id}: changes between two screenshots 1 s apart`);
  }
}
await motionCheck(b, false);
const rb = await chrome(9342, ['--force-prefers-reduced-motion']);
await motionCheck(rb, true);
rb.close();

// ---- 4. mirror symmetry of the device icons
console.log('\n[device icon symmetry]');
const blankPage = path.join(mkdtempSync(path.join(tmpdir(), 'sym-')), 'blank.html');
writeFileSync(blankPage, '<!doctype html><html><body></body></html>');
await b.load('file://' + blankPage, 800, 'light', 1);
for (const f of svgFiles.filter((x) => /^card-idevice-control/.test(x))) {
  const src = readFileSync(path.join(ASSETS, f), 'utf8');
  const res = await b.eval(`(async () => {
    const doc = new DOMParser().parseFromString(${JSON.stringify(src)}, 'image/svg+xml');
    const host = document.createElement('div'); document.body.append(host);
    host.append(document.importNode(doc.documentElement, true));
    const out = [];
    for (const id of ['fx0', 'fx1', 'fx2']) {
      const g = host.querySelector('#' + id), bb = g.getBBox(), Z = 8;
      const x = bb.x - 1, y = bb.y - 1, w = bb.width + 2, h = bb.height + 2;
      const clone = g.cloneNode(true);
      clone.querySelectorAll('.pm').forEach((e) => e.remove());
      const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + [x, y, w, h].join(' ') + '" width="' + w * Z + '" height="' + h * Z + '">' +
        new XMLSerializer().serializeToString(clone) + '</svg>';
      const img = new Image(); img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg); await img.decode();
      const W = Math.round(w * Z), H = Math.round(h * Z);
      const c1 = new OffscreenCanvas(W, H).getContext('2d'), c2 = new OffscreenCanvas(W, H).getContext('2d');
      c1.drawImage(img, 0, 0, W, H);
      c2.translate(W, 0); c2.scale(-1, 1); c2.drawImage(img, 0, 0, W, H);
      const d1 = c1.getImageData(0, 0, W, H).data, d2 = c2.getImageData(0, 0, W, H).data;
      let sum = 0, off = 0;
      for (let i = 0; i < d1.length; i += 4) {
        let px = 0; for (let k = 0; k < 4; k++) px = Math.max(px, Math.abs(d1[i + k] - d2[i + k]));
        sum += px; if (px > 64) off++;
      }
      out.push([id, sum / (d1.length / 4) / 2.55, off / (d1.length / 4) * 100]);
    }
    host.remove();
    return out;
  })()`);
  for (const [id, mean, off] of res) check(off < 0.5, `${f} ${id}: mirror image differs by ${mean.toFixed(2)}% on average, ${off.toFixed(2)}% of pixels by more than 25%`);
}

// ---- 7. geometry: repo name vs diamond, heading tags, easter-egg images
console.log('\n[geometry]');
await b.load('file://' + blankPage, 800, 'light', 1);
// Inlines one SVG and returns the boxes of the given selectors in viewBox units: [left, top, right, bottom].
const boxes = (src, sels) => b.eval(`(() => {
  const doc = new DOMParser().parseFromString(${JSON.stringify(src)}, 'image/svg+xml');
  const host = document.createElement('div'); document.body.append(host);
  const svg = document.importNode(doc.documentElement, true); host.append(svg);
  const inv = svg.getScreenCTM().inverse();
  const user = (e) => { const q = e.getBoundingClientRect(), a = new DOMPoint(q.left, q.top).matrixTransform(inv), z = new DOMPoint(q.right, q.bottom).matrixTransform(inv); return [a.x, a.y, z.x, z.y]; };
  const out = { vb: [svg.viewBox.baseVal.x, svg.viewBox.baseVal.y, svg.viewBox.baseVal.width, svg.viewBox.baseVal.height] };
  for (const [k, sel] of Object.entries(${JSON.stringify(sels)})) {
    const e = svg.querySelector(sel);
    out[k] = e ? user(e) : null;
    if (e) out[k + 'Stroke'] = parseFloat(e.getAttribute('stroke-width') || 0);
    if (e && e.tagName === 'rect') out[k + 'Attr'] = ['x', 'y', 'width', 'height'].map((a) => +e.getAttribute(a));
  }
  host.remove();
  return out;
})()`);
for (const f of svgFiles.filter((x) => /^card-(?!back)/.test(x))) {
  const v = /-phone-/.test(f) ? 'phone' : 'wide';
  const g = await boxes(readFileSync(path.join(ASSETS, f), 'utf8'), { nm: '.nm', dia: 'path[fill="#e1ab31"]', band: '.band', card: '#cc rect' });
  const tip = g.dia[2] + g.diaStroke / 2;          // round join: the outline reaches half the stroke past the tip
  const gap = g.nm[0] - tip, margin = g.cardAttr[2] - g.nm[2];
  const [, by, , bh] = g.bandAttr, above = g.nm[1] - by, below = by + bh - g.nm[3];
  check(Math.abs(gap - TITLE_GAP[v]) <= 0.5 && margin >= TITLE_MARGIN - 0.05 && above >= 4 && below >= 4,
    `${f}: name ${gap.toFixed(2)}px right of the diamond tip (want ${TITLE_GAP[v]}), ${margin.toFixed(2)}px from the card's right edge (want >=${TITLE_MARGIN}), ` +
    `${above.toFixed(1)}px / ${below.toFixed(1)}px inside the band top / bottom`);
}
for (const f of svgFiles.filter((x) => /^h-/.test(x))) {
  const v = /-phone-/.test(f) ? 'phone' : 'wide';
  const g = await boxes(readFileSync(path.join(ASSETS, f), 'utf8'), { lb: '.lb', box: '.box', chip: 'path[fill="#4a68b0"]' });
  const h = g.vb[3], s = h / 36, cap = g.lb[3] - g.lb[1], mid = (g.lb[1] + g.lb[3]) / 2;
  // the box is skewed; at mid-height its right edge sits half its height times tan(14) left of its bounding right edge
  const boxH = g.boxAttr[3], boxRight = g.box[2] - (boxH / 2) * Math.tan(14 * Math.PI / 180);
  const pad = boxRight - g.lb[2], chipLeft = g.chip[0] - 1.3 * 0.9 * s;
  check(Math.abs(cap - HEAD_CAP[v]) <= 0.4 && Math.abs(mid - h / 2) <= 0.5 && pad >= 6 && g.lb[0] > g.chip[2] && Math.abs(chipLeft) <= 0.3,
    `${f}: label cap ${cap.toFixed(2)}px (want ${HEAD_CAP[v].toFixed(2)}), centre ${(mid - h / 2).toFixed(2)}px off the tag middle, ` +
    `${pad.toFixed(1)}px clear of the box's right edge, chip left edge at x=${chipLeft.toFixed(2)}`);
}
for (const f of svgFiles.filter((x) => /^egg-/.test(x))) {
  const g = await boxes(readFileSync(path.join(ASSETS, f), 'utf8'), { tx: '.tx' });
  const [, , w, h] = g.vb, inside = g.tx[0] >= 0 && g.tx[1] >= 0 && g.tx[2] <= w && g.tx[3] <= h;
  const sum = /^egg-summary/.test(f), base = h - g.tx[3];
  check(inside && (!sum || base >= 0 && base <= 1.5),
    `${f}: ${w}x${h}, text ink [${g.tx.map((x) => x.toFixed(1)).join(', ')}] inside the viewBox${sum ? `, ink bottom ${base.toFixed(2)}px above the image bottom (the baseline)` : ''}`);
}

// ---- 5. side-by-side shots with the references
console.log('\n[compare shots]');
const A = (f) => `file://${ASSETS}/${f}`;
const R = (f) => `file://${path.join(REF, f)}`;
// crop(src, x, y, w, h, height): shows the w x h box at (x, y) of an image, scaled to `height` px.
const crop = (src, x, y, w, h, height, label) => {
  const s = height / h;
  return `<figure><div class="crop" style="width:${w * s}px;height:${height}px"><img src="${src}" style="left:${-x * s}px;top:${-y * s}px;height:auto;width:var(--iw)" data-s="${s}"></div><figcaption>${label}</figcaption></figure>`;
};
const card = (f, label, height = 403) => `<figure><img src="${A(f)}" style="height:${height}px"><figcaption>${label}</figcaption></figure>`;
// a zoomed part of a wide card SVG (281 x 403 slot units; the middle card sits 9.5 units into its slot)
const zoom = (f, x, y, w, h, z, label, src = A(f)) => `<figure><div class="crop" style="width:${w * z}px;height:${h * z}px"><img src="${src}" style="left:${-x * z}px;top:${-y * z}px;width:${281 * z}px"></div><figcaption>${label}</figcaption></figure>`;
const page = (rows) => `<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font:600 13px -apple-system,Helvetica,sans-serif}
.row{display:flex;gap:18px;align-items:flex-start;padding:16px 20px;flex-wrap:wrap}.light{background:#f6f8fa;color:#57606a}.dark{background:#0d1117;color:#9198a1}
figure{margin:0}figcaption{margin-top:6px;max-width:420px}.crop{position:relative;overflow:hidden;border-radius:4px}.crop img{position:absolute}
</style></head><body>${rows}<script>for(const i of document.querySelectorAll('.crop img[data-s]'))i.onload=()=>{i.style.width=(i.naturalWidth*i.dataset.s)+'px'};</script></body></html>`;
const ID = 'card-idevice-control', CC = 'card-cc-session-breakdown', MID = 9.5;
const frontRows =
  `<div class="row light">${crop(R('cards/sample-gateway-to-mars.png'), 72, 137, 583, 811, 403, 'SETI reference: Gateway to Mars')}` +
  `${crop(R('web/front-pluto-promo-flat-1.png'), 22, 20, 562, 786, 403, 'SETI reference: Pluto promo (flat)')}` +
  `${card(ID + '-light.svg', 'profile idevice-control · light')}${card(CC + '-light.svg', 'profile cc-session-breakdown · light')}</div>` +
  `<div class="row dark">${crop(R('web/front-niac-program-full-1.png'), 10, 10, 740, 990, 403, 'SETI reference: NIAC Program (photo)')}` +
  `${crop(R('web/art-apollo-soyuz-1.png'), 0, 0, 800, 497, 190, 'SETI art reference (painted depth)')}` +
  `${card(ID + '-dark.svg', 'profile idevice-control · dark')}${card(CC + '-dark.svg', 'profile cc-session-breakdown · dark')}</div>` +
  `<div class="row light">${zoom(ID + '-light.svg', 0, 0, 60, 60, 3.2, 'profile: dish corner and planet')}${zoom(CC + '-dark.svg', MID, 0, 60, 60, 3.2, 'profile: dish corner · dark')}` +
  `${crop(R('web/front-sector-corner-signal-niac-1.png'), 0, 0, 800, 1006, 190, 'ref: blue signal corner')}` +
  `${zoom(ID + '-light.svg', 212, 0, 50, 50, 3.6, 'profile: blue signal')}${zoom(CC + '-light.svg', 212 + MID, 0, 50, 50, 3.6, 'profile: red signal')}</div>` +
  `<div class="row light">${zoom(ID + '-light.svg', 0, 154, 120, 70, 2.7, 'profile: gold diamond on the blue band')}` +
  `${zoom(CC + '-light.svg', MID, 154, 120, 70, 2.7, 'profile: gold diamond on the red band')}</div><div class="row light">` +
  `${crop(R('web/front-income-energy-corner-venus-render-1.png'), 0, 200, 800, 520, 190, 'ref: energy income')}` +
  `${zoom(ID + '-light.svg', 182, 355, 80, 48, 3.6, 'profile: energy income')}` +
  `${crop(R('web/front-income-credit-corner-falcon-heavy-render-1.png'), 0, 200, 800, 520, 190, 'ref: credit income')}` +
  `${zoom(CC + '-light.svg', 182 + MID, 355, 80, 48, 3.6, 'profile: credit income')}</div>` +
  `<div class="row light">${crop(R('cards/sample-gateway-to-mars.png'), 150, 690, 400, 130, 190, 'ref: white notched tokens')}` +
  `${crop(R('web/front-falcon-heavy-3-icons-render-1.png'), 200, 500, 400, 210, 190, 'ref: three effect icons')}` +
  `${zoom(ID + '-light.svg', 44, 290, 192, 70, 2.7, 'profile: iPhone, iPad, TV below the text · light')}</div>` +
  `<div class="row dark">${zoom(ID + '-dark.svg', 44, 290, 192, 70, 2.7, 'profile: iPhone, iPad, TV · dark')}` +
  `${zoom(CC + '-light.svg', 14 + MID, 238, 82, 84, 2.7, 'profile: pie chart left of the text · light')}` +
  `${zoom(CC + '-dark.svg', 14 + MID, 238, 82, 84, 2.7, 'profile: pie chart · dark')}</div>`;
const backRows =
  `<div class="row light">${crop(R('web/back-main-deck-flat-pluto-promo-1.png'), 24, 20, 562, 786, 403, 'SETI reference: main-deck back (flat)')}` +
  `${crop(R('web/front-falcon-heavy-3-icons-render-1.png'), 0, 0, 300, 340, 403, 'SETI reference: VLA dishes (Very Large Array card)')}` +
  `${card('card-back-light.svg', 'profile draw pile · light')}</div>` +
  `<div class="row dark">${crop(R('web/pile-main-deck-stack-1.png'), 0, 0, 800, 700, 403, 'SETI reference: draw pile (photo)')}` +
  `${card('card-back-dark.svg', 'profile draw pile · dark')}${zoom('card-back-light.svg', 140, 312, 141, 91, 2.7, 'profile: pile edges, zoomed')}</div>`;

// the draw pile: reference photo, the page-v9 poster pile with flat edge strips, the current pile
const V9 = (f) => `file://${path.join(V9_DIR, f)}`;
const pileRows = ['light', 'dark'].map((t) =>
  `<div class="row ${t}">${crop(R('web/pile-main-deck-stack-1.png'), 0, 20, 760, 650, 403, 'SETI reference: draw pile (photo)')}` +
  `<figure><img src="${V9(`card-back-poster-${t}.svg`)}" style="height:403px"><figcaption>v9 Option A pile · ${t}</figcaption></figure>` +
  `${card(`card-back-${t}.svg`, `profile pile · ${t}`)}` +
  `${zoom('', 0, 323, 110, 80, 2.4, 'v9: bottom-left corner', V9(`card-back-poster-${t}.svg`))}` +
  `${zoom(`card-back-${t}.svg`, 0, 323, 110, 80, 2.4, 'profile: bottom-left corner')}</div>`).join('');

// first design (page-v3: 420 x 587 cards in a 426-unit image, the right card 6 units into it) next to the current cards
const FIRST = (f) => `file://${path.join(FIRST_DIR, f)}`;
const native = (src, w, label) => `<figure><img src="${src}" style="width:${w}px"><figcaption>${label}</figcaption></figure>`;
const zoomW = (src, x, y, w, h, z, fullW, label) => `<figure><div class="crop" style="width:${w * z}px;height:${h * z}px"><img src="${src}" style="left:${-x * z}px;top:${-y * z}px;width:${fullW * z}px"></div><figcaption>${label}</figcaption></figure>`;
const firstRows = ['light', 'dark'].map((t) =>
  `<div class="row ${t}">${native(FIRST(`${ID}-${t}.svg`), 426, `first design idevice-control · ${t}`)}` +
  `${native(FIRST(`${CC}-${t}.svg`), 426, `first design cc-session-breakdown · ${t}`)}` +
  `${native(A(`${ID}-${t}.svg`), 281, `profile idevice-control · ${t}`)}${native(A(`${CC}-${t}.svg`), 281, `profile cc-session-breakdown · ${t}`)}</div>`).join('') +
  `<div class="row light"><div style="width:100%">Corner and title area, same zoom (2x)</div>` +
  `${zoomW(FIRST(ID + '-light.svg'), 0, 0, 104, 104, 2, 426, 'first design: dish corner')}` +
  `${zoomW(A(ID + '-light.svg'), 0, 0, 65, 65, 2, 281, 'profile: dish corner')}` +
  `${zoomW(FIRST(ID + '-light.svg'), 0, 262, 300, 108, 2, 426, 'first design: diamond and band')}` +
  `${zoomW(A(ID + '-light.svg'), 0, 154, 262, 70, 2, 281, 'profile: diamond and band')}</div>`;

// ---- 6. title-font candidates
const tfDir = mkdtempSync(path.join(tmpdir(), 'tf-'));
execFileSync('python3', [path.join(HERE, 'gen', 'cards', 'build_cards.py'), '--title-fonts', tfDir]);
const used = readFileSync(path.join(HERE, 'gen', 'cards', 'build_cards.py'), 'utf8').match(/^TITLE_FONT = '(\w+)'/m)[1];
const FONT_LABEL = {
  pixel: 'Pixel 5 x 7: the header banner font (gen/tools/pixelfont.py), 1.5 px cells',
  jost: 'Jost Medium 500: the body font (fonts/jost/Jost[wght].ttf, SIL OFL), 17.5 px',
  oxanium: 'Oxanium Bold 700, white: squared like the header wordmark (fonts/oxanium/Oxanium[wght].ttf, SIL OFL), 18 px',
};
const tfRows = Object.keys(FONT_LABEL).map((font) =>
  `<div class="row light"><div style="width:100%">${FONT_LABEL[font]}${font === used ? ' · USED ON THE CARDS' : ''}</div>` +
  ['idevice-control', 'cc-session-breakdown'].map((n) => zoom('', 0, 155, 262, 68, 2.4, n, `file://${tfDir}/title-${font}-${n}.svg`)).join('') +
  '</div>').join('');
for (const [name, rows, width, needs] of [['compare-front', frontRows, 1380, [REF]], ['compare-back', backRows, 1320, [REF]],
  ['title-fonts', tfRows, 1340, []], ['compare-first-design', firstRows, 1520, [FIRST_DIR]], ['pile-compare', pileRows, 1720, [REF, V9_DIR]]]) {
  const missing = needs.filter((d) => !existsSync(d));
  if (missing.length) { console.log(`skip shots/${name}.png: missing ${missing.map((d) => path.relative(HERE, d)).join(', ')}`); continue; }
  const file = path.join(mkdtempSync(path.join(tmpdir(), 'cmp-')), name + '.html');
  writeFileSync(file, page(rows));
  await b.load('file://' + file, width, 'light', 2, 'no-preference', 300);
  await sleep(1200);
  const hgt = await b.eval('document.documentElement.scrollHeight');
  await b.shot(path.join(HERE, 'shots', name + '.png'), { x: 0, y: 0, width, height: hgt });
  console.log(`saved shots/${name}.png (${width}x${hgt} css px)`);
}
// ---- 8. easter egg opened, all four preview frames
console.log('\n[easter egg opened]');
await b.load('file://' + path.join(HERE, 'index.html'), 1900, 'light', 2);
const opened = await b.eval(`(() => {
  const out = [];
  for (const sec of document.querySelectorAll('section')) {
    const md = sec.querySelector('.markdown-body'), d = md.querySelector('details');
    for (const el of md.children) if (el !== d) el.style.display = 'none';
    d.open = true;
    const img = [...d.querySelectorAll('img')].find((i) => !d.querySelector('summary').contains(i) && !i.getAttribute('src').endsWith('/blank.svg'));
    out.push([sec.id, img.getAttribute('src').split('/').pop(), img.getBoundingClientRect().width]);
  }
  const g = document.querySelector('.grid').getBoundingClientRect();
  return { out, clip: { x: g.x, y: g.y + scrollY, width: g.width, height: g.height } };
})()`);
for (const [frame, file, w] of opened.out) {
  const t = TEXT[stem(file)], scale = w / viewBoxW[file], size = t.text * scale, want = frame.startsWith('phone') ? 14 : 15;
  check(w > 0 && Math.abs(size - want) < 0.05, `${frame}: opened, ${file} shown ${w.toFixed(1)}px wide, text ${size.toFixed(1)}px (want ${want}, the About size)`);
}
await b.shot(path.join(HERE, 'shots', 'details-open.png'), opened.clip);
console.log(`saved shots/details-open.png (${Math.round(opened.clip.width)}x${Math.round(opened.clip.height)} css px)`);
b.close();
console.log('\n[svg sizes] ' + sizes.join(' | '));
console.log(fails.length ? `\n${fails.length} check(s) failed` : '\nall checks passed');
process.exitCode = fails.length ? 1 : 0;
