"""Builds the SETI-style project cards as self-contained, animated SVGs.

Run: python3 build_cards.py [out_dir]   (default: ../../../assets, the README assets folder)
     python3 build_cards.py --title-fonts <dir>   writes the title-band comparison SVGs instead
Needs ../icons/seti_icons.json (made by ../icons/extract_icons.py).

Output, each in a light and a dark version (-light.svg, -dark.svg):
- card-idevice-control, card-cc-session-breakdown: wide screens, one 281 px slot each.
  Three slots fill one row of GitHub's 846 px README width (3 x 281 = 843). Each card is 262 x 403
  (width:height 0.650) inside its slot; the transparent rest of the slot is the gutter. Slot
  positions: idevice-control left, cc-session-breakdown middle, the draw pile (card-back, made by
  ../back/build_back.py from LAYOUT['wide']) right, so the row's outer card edges sit 1.5 px inside
  the header edges and the two gaps between cards are 28.5 px each.
- card-idevice-control-phone, card-cc-session-breakdown-phone: narrow screens. A short wide card,
  viewBox 293 px wide (the README width on a 375 px phone, where 1 unit = 1 px), intrinsic width
  PHONE_MAX. The README sets no width attribute, so each card renders at its own size, capped by
  GitHub's max-width:100%: it fills the README width on every phone up to PHONE_MAX, and two
  cards never fit on one line, so they stack.
- blank.svg: 0 x 0 image. The card-back slot shows it where the row has no room for three cards.

Card front anatomy (W = card width). Everything except the illustration and its small planet is
flat: solid fills, no gradients, bevels or shadows.
- illustration on top, the one dimensional part of the card;
- a dark 45 degree triangle at the top left (legs = the sector triangle's) with the white radio
  dish, and a small orange planet in the sky just off its long edge;
- a sector-colour 45 degree triangle at the top right (legs 0.16 W) with the white signal icon, its
  bars pulsing;
- a full-width band in the sector colour (thin light line on top, darker line along the bottom)
  with the repo name in white, vertically centred, its leftmost ink TITLE_GAP right of the diamond's
  right tip;
- a gold diamond centred on the band's height at its left end, with a dark outline, a pale inner
  line and the project icon: idevice-control a phone with a tap, cc-session-breakdown a pie with
  one slice pulled out;
- a pale effect panel with faint stars and the one line. Effect icons follow the SETI rule:
  1 icon left of the text, 2 icons above it, 3 icons below it, each in a plain white circular token
  with a thin edge, the coloured disc and its white icon centred in it;
- a flavour strip with the italic flavour line and a rotated card code at the far left;
- the income corner at the bottom right (right-angled trapezoid, 45 degree left edge) plus a strip
  of the same colour along the whole bottom edge. idevice-control: energy (green),
  cc-session-breakdown: credit (gold).
The credit, energy and signal icons are the fan-site SETI icons traced to outlines
(../icons/seti_icons.json), placed on shapes drawn here.

Every size below is in CSS px at the README width the variant is made for.
Body text is glyph outlines from BODY_FONT via ../tools/ttfpath.py. The repo name uses TITLE_FONT,
Oxanium Bold 700, white on the sector band (contrast asserted >= 4:1, the band text is >= 18 px
bold). The section heading tags (../headings.py) use Oxanium too. The other title-font
candidates, shown only by --title-fonts: 'pixel' (the 5 x 7 pixel font of the header banner,
../tools/pixelfont.py) and 'jost'.
The device icons are built from shapes that are their own mirror image; check_symmetry() asserts it.
Motion is CSS only; the prefers-reduced-motion rule in STYLE stops all of it.
"""
import json
import math
import pathlib
import random
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools'))
from ttfpath import TTF  # noqa: E402
import pixelfont  # noqa: E402

# ---------------------------------------------------------------- type
# The one body font of the page: Jost (SIL OFL 1.1), variable weight axis 100-900, upright + italic.
FONT_DIR = HERE.parents[1] / 'fonts' / 'jost'
BODY_FONT = {'upright': FONT_DIR / 'Jost[wght].ttf', 'italic': FONT_DIR / 'Jost-Italic[wght].ttf'}
# Oxanium (SIL OFL 1.1), variable weight 200-800: the repo-name font on the title band.
OXANIUM = HERE.parents[1] / 'fonts' / 'oxanium' / 'Oxanium[wght].ttf'
# m: the one line, f: flavour line (italic), c: card code,
# to: repo name in Oxanium Bold, tj: repo name in Jost (a title-font candidate)
WEIGHTS = {'m': 470, 'f': 420, 'c': 640, 'tj': 500}
ITALIC = {'f'}
FONTS = {k: TTF(str(BODY_FONT['italic' if k in ITALIC else 'upright']), wght=w) for k, w in WEIGHTS.items()}
FONTS['to'] = TTF(str(OXANIUM), wght=700)

TITLE_FONT = 'oxanium'
# Repo name size per title font and variant: pixel = px per font cell, others = font size in px.
TITLE_SIZE = {'pixel': {'wide': 1.5, 'phone': 5 / 3}, 'jost': {'wide': 17.5, 'phone': 19},
              'oxanium': {'wide': 18, 'phone': 20}}
TITLE_TRACK = {'oxanium': -35, 'jost': 0}   # letter spacing in font units (1000 per em)
TITLE_FILL = '#ffffff'
# Diamond's right tip (outline included) to the leftmost ink of the name, horizontal, in px:
# about 0.6 of the name's font size.
TITLE_GAP = {'wide': 11, 'phone': 12}
TITLE_MARGIN = 7     # ink of the last letter to the card's right edge, at least

PHONE_MAX = 400
PHONE_GAP = 6     # transparent strip under each phone card; with the line box it spaces stacked cards ~12 px

# Flat SETI palette (sampled from the printed cards and the fan-site icons).
GOLD = '#ad9636'
GOLD_DARK = '#7d6b1f'
GREEN = '#7fa645'
BLUE = '#3578d8'
RED = '#e0442a'
SETI_GREEN = '#3c9f2c'
SETI_GOLD = '#c19a2b'
# Title area and top-left corner, from the first card design.
CORNER = '#141924'     # top-left triangle
INK = '#0e121a'        # diamond outline and the outlines inside its icons
DIAMOND = '#e1ab31'    # diamond fill: the first design's gold, flat
DIAMOND_LINE = '#fff6d6'

# Card geometry per variant.
# sector: leg of both top triangles (top-left dark corner, top-right sector colour).
# dish: radio dish centre x, y, scale (the icon is 26 units tall). planet: centre x, y, radius.
# band: top, height. diamond: centre x, half diagonal (centre y = the band's middle).
# panel: left x, top, bottom. line: text size, line pitch.
# tok3: token centre y, radius, spacing (3 icons below the text). tok1: token radius (1 icon left).
# flav: flavour line x, baseline, size. code: card-code box x, top, width, height, font size.
# income: corner height, top edge, bottom edge; strip: bottom strip height.
LAYOUT = {
    'wide': dict(slot=281, cw=262, ch=403, r=10.5, sector=42, dish=(13, 13.5, .62), planet=(25, 31.5, 4),
                 band=(173, 32), diamond=(36, 29), panel=(16.5, 222, 340), line=(16, 21.5),
                 tok3=(326, 27, 64), tok1=31, flav=(45, 381, 10.5), code=(3.3, 348, 9.4, 37, 6.6),
                 income=(37, 37, 68), strip=8),
    'phone': dict(slot=293, cw=293, ch=236, r=10.5, sector=40, dish=(12.5, 13, .6), planet=(24, 30, 3.8),
                  band=(82, 34), diamond=(37, 27), panel=(17, 130, 190), line=(15, 19.5),
                  tok3=(188, 19, 46), tok1=24, flav=(47, 223, 10.5), code=(3.3, 193, 9.4, 34, 6.4),
                  income=(32, 34, 66), strip=7),
}

# Colours of the card's light areas per GitHub theme.
THEMES = {
    'light': {'body': '#ffffff', 'panel': '#e6edf4', 'panel_line': '#cfd9e4', 'star': .95, 'text': '#1d1f21',
              'flav': '#45484c', 'edge': '#d1d9e0', 'code_bg': '#e9e9e9', 'code': '#3c3f42', 'tok': '#ffffff',
              'tok_line': '#c3ccd6'},
    'dark':  {'body': '#161d26', 'panel': '#212e3d', 'panel_line': '#2c3b4d', 'star': .35, 'text': '#e6edf3',
              'flav': '#9198a1', 'edge': '#30363d', 'code_bg': '#252c35', 'code': '#9198a1', 'tok': '#f4f6f8',
              'tok_line': '#c3ccd6'},
}

STYLE = ('.t1{animation:tw 2.8s ease-in-out infinite alternate}'
         '.t2{animation:tw 3.9s ease-in-out -1.3s infinite alternate}'
         '.t3{animation:tw 5.2s ease-in-out -2.4s infinite alternate}'
         '@keyframes tw{from{opacity:1}to{opacity:.15}}'
         '%s'
         '@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }')

# Motion shared by both fronts: the signal bars pulse like a level meter, each on its own beat
# (the dots stay), and the faint panel stars twinkle.
FRONT_STYLE = (
    '.eq{transform-box:fill-box;transform-origin:center;animation:eq 1.2s ease-in-out infinite alternate}'
    '.e2{animation-duration:.9s;animation-delay:-.5s}.e3{animation-duration:1.5s;animation-delay:-.2s}'
    '@keyframes eq{from{transform:scaleY(1)}to{transform:scaleY(.45)}}'
    '.pst{animation:tw 3.4s ease-in-out infinite alternate}'
)

def f(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def poly(p):
    return 'M' + 'L'.join('%s %s' % (f(x), f(y)) for x, y in p) + 'Z'


class Doc:
    """Collects the glyph defs used by one SVG."""

    def __init__(self):
        self.glyphs = {}

    def text(self, font, s, x, y, size, anchor='start', fill='#000', tracking=0, outline=None, rotate=0, extra=''):
        """Glyph outlines with the baseline start at (x, y). outline: (colour, width in px) drawn under the fill."""
        fnt = FONTS[font]
        items, w = fnt.layout(s, tracking)
        sc = size / fnt.upm
        if anchor == 'middle':
            x -= w * sc / 2 if not rotate else 0
        elif anchor == 'end':
            x -= w * sc
        uses = []
        for g, gx in items:
            key = '%s%x' % (font, g)
            if key not in self.glyphs:
                self.glyphs[key] = fnt.glyph_d(g)
            if self.glyphs[key]:
                uses.append('<use href="#%s" x="%d"/>' % (key, gx))
        tr = 'translate(%s %s)' % (f(x), f(y))
        if rotate:
            tr += ' rotate(%g)' % rotate
            if anchor == 'middle':
                tr += ' translate(%s 0)' % f(-w * sc / 2)
        tr += ' scale(%.6f)' % sc
        out = ''
        if outline:
            out = ('<g transform="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round">%s</g>'
                   % (tr, outline[0], outline[0], f(outline[1] * 2 / sc), ''.join(uses)))
        return out + '<g transform="%s" fill="%s"%s>%s</g>' % (tr, fill, extra, ''.join(uses))

    def defs(self):
        return ''.join('<path id="%s" d="%s"/>' % (k, d) for k, d in self.glyphs.items() if d)


def width(font, s, size, tracking=0):
    fnt = FONTS[font]
    return fnt.layout(s, tracking)[1] * size / fnt.upm


def wrap(font, s, size, maxw, most=3):
    """Splits s into the fewest lines (up to `most`) that fit maxw, as even in width as possible.
    No line holds a single word; "Claude Code" stays on one line."""
    words = s.replace('Claude Code', 'Claude\u00a0Code').split(' ')
    for n in range(1, most + 1):
        best = None
        for cut in _cuts(len(words), n):
            lines = [' '.join(words[a:b]).replace('\u00a0', ' ') for a, b in zip((0,) + cut, cut + (len(words),))]
            if n > 1 and any(' ' not in ln for ln in lines):
                continue
            wmax = max(width(font, ln, size) for ln in lines)
            if wmax <= maxw and (best is None or wmax < best[0]):
                best = (wmax, lines)
        if best:
            return best[1]
    raise AssertionError((s, size, maxw))


def _cuts(n, parts):
    """Every way to cut n words into `parts` non-empty runs, as tuples of cut positions."""
    if parts == 1:
        yield ()
        return
    for i in range(1, n):
        for rest in _cuts(n - i, parts - 1):
            yield (i,) + tuple(i + r for r in rest)


def annulus(r0, r1, a0, a1):
    """Ring sector around (0, 0), angles in degrees clockwise from 12 o'clock."""
    def pt(r, a):
        t = math.radians(a - 90)
        return r * math.cos(t), r * math.sin(t)
    large = 1 if a1 - a0 > 180 else 0
    p1, p2, p3, p4 = pt(r1, a0), pt(r1, a1), pt(r0, a1), pt(r0, a0)
    return ('M%.2f %.2fA%g %g 0 %d 1 %.2f %.2fL%.2f %.2fA%g %g 0 %d 0 %.2f %.2fZ'
            % (p1 + (r1, r1, large) + p2 + p3 + (r0, r0, large) + p4))


def wedge(r, a0, a1):
    """Pie slice around (0, 0), angles in degrees clockwise from 12 o'clock."""
    t0, t1 = math.radians(a0 - 90), math.radians(a1 - 90)
    return 'M0 0L%.2f %.2fA%g %g 0 %d 1 %.2f %.2fZ' % (
        r * math.cos(t0), r * math.sin(t0), r, r, 1 if a1 - a0 > 180 else 0, r * math.cos(t1), r * math.sin(t1))


def stars(seed, n, avoid, x0, y0, x1, y1, size=1.0, fill='#fff', op=(0.45, 0.95), twinkle=True):
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid):
            continue
        r = rnd.choice((0.45, 0.55, 0.65, 0.8, 1.0)) * size
        cls = rnd.choice(('t1', 't2', 't3', '', '')) if twinkle else ''
        out.append('<circle cx="%.1f" cy="%.1f" r="%s" fill="%s" opacity="%.2f"%s/>' % (
            x, y, f(r), fill, rnd.uniform(*op), (' class="%s"' % cls) if cls else ''))
    return ''.join(out)


def place(x, y, s, rot=0):
    return 'translate(%s %s)%s scale(%s)' % (f(x), f(y), ' rotate(%g)' % rot if rot else '', f(s))


# ---------------------------------------------------------------- paint helpers

def _stops(stops):
    return ''.join('<stop offset="%s" stop-color="%s"%s/>' % (f(o), c, (' stop-opacity="%s"' % f(a)) if a < 1 else '')
                   for o, c, a in stops)


def lin(id_, stops, x1=0, y1=0, x2=0, y2=1, user=False):
    """Linear gradient. stops: [(offset, colour, opacity)]."""
    return ('<linearGradient id="%s" x1="%s" y1="%s" x2="%s" y2="%s"%s>%s</linearGradient>'
            % (id_, f(x1), f(y1), f(x2), f(y2), ' gradientUnits="userSpaceOnUse"' if user else '', _stops(stops)))


def rad(id_, stops, cx=.5, cy=.5, r=.5, user=False):
    return ('<radialGradient id="%s" cx="%s" cy="%s" r="%s"%s>%s</radialGradient>'
            % (id_, f(cx), f(cy), f(r), ' gradientUnits="userSpaceOnUse"' if user else '', _stops(stops)))


def blur(id_, sd):
    return ('<filter id="%s" x="-50%%" y="-50%%" width="200%%" height="200%%" color-interpolation-filters="sRGB">'
            '<feGaussianBlur stdDeviation="%s"/></filter>' % (id_, f(sd)))


def mix(a, b, t):
    """Blends hex colours a -> b by t."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


# Shared filters: soft shadow, glow and haze blurs.
FILTERS = (blur('b1', 1) + blur('b2', 2) + blur('b4', 4) + blur('b8', 8) +
           '<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" '
           'numOctaves="2" seed="7" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 1.4 -.55"/></filter>')


def grain(w, h, op=.07):
    """Fine painted grain over an illustration."""
    return '<rect width="%s" height="%s" filter="url(#grain)" opacity="%s"/>' % (f(w), f(h), f(op))


def shadow(shape, dx=0, dy=1.4, op=.35, flt='b1'):
    """Soft drop shadow: the shape in black, offset and blurred."""
    return '<g transform="translate(%s %s)" opacity="%s" filter="url(#%s)">%s</g>' % (f(dx), f(dy), f(op), flt, shape)




# ---------------------------------------------------------------- SETI icons (traced from the fan-site sheet)
# 100-unit grid per icon: the sprite cell spans -50..50, centre (0, 0), y down.

SETI = json.loads((HERE.parent / 'icons' / 'seti_icons.json').read_text(encoding='utf-8'))['icons']


def seti_outlines(name, layer='glyph'):
    return SETI[name]['layers'][layer]


def seti_bbox(name, layer='glyph'):
    bs = [o['bbox'] for o in seti_outlines(name, layer)]
    return min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)


def seti_path(name, fill='#fff', layer='glyph', centre=True):
    """One icon layer as a single evenodd path, centred on its bounding box when `centre`."""
    d = ''.join(o['d'] for o in seti_outlines(name, layer))
    out = '<path fill="%s" fill-rule="evenodd" d="%s"/>' % (fill, d)
    if centre:
        x0, y0, x1, y1 = seti_bbox(name, layer)
        out = '<g transform="translate(%s %s)">%s</g>' % (f(-(x0 + x1) / 2), f(-(y0 + y1) / 2), out)
    return out


def credit_glyph(fill='#fff'):
    """White credit glyph, centred, 72 units tall."""
    return seti_path('credit', fill)


def bolt(fill='#fff'):
    """White energy bolt, centred, 74 units tall."""
    return seti_path('energy', fill)


def signal_icon(name):
    """White signal mark centred on (0, 0); every bar taller than it is wide pulses on its own beat."""
    outs = seti_outlines(name)
    x0, y0, x1, y1 = seti_bbox(name)
    out, k = [], 0
    for o in outs:
        bx0, by0, bx1, by1 = o['bbox']
        cls = ''
        if by1 - by0 > 1.5 * (bx1 - bx0):
            cls = ' class="eq%s"' % ('', ' e2', ' e3')[k % 3]
            k += 1
        out.append('<path%s d="%s"/>' % (cls, o['d']))
    return '<g fill="#fff" transform="translate(%s %s)">%s</g>' % (f(-(x0 + x1) / 2), f(-(y0 + y1) / 2), ''.join(out))


def signal_fit(name, k, m=3.6, mh=5):
    """Largest scale s and centre offset c for a signal icon centred on the corner diagonal at
    (cw - c, c) that keeps it inside the triangle with legs k: margin m to the card edges, mh
    (in x + y) to the hypotenuse."""
    x0, y0, x1, y1 = seti_bbox(name)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    pts_ = []
    for o in seti_outlines(name):
        for pair in o['d'][1:-1].split('L'):
            x, y = map(float, pair.split())
            pts_.append((x - cx, y - cy))
    e = max(max(x for x, _ in pts_), max(-y for _, y in pts_))
    d = max(y - x for x, y in pts_)
    s = (k - mh - 2 * m) / (2 * e + d)
    return s, m + e * s


# ---------------------------------------------------------------- top-left corner and title diamond (first design)

def icon_dish():
    """White radio dish on a stand, aimed up-left, about 19 x 26 units, centred on (0, 0)."""
    return ('<g transform="translate(0 -1)" fill="#fff" stroke="#fff" stroke-linecap="round" stroke-linejoin="round">'
            '<g transform="rotate(-40 0 -1)"><path d="M-11 -1A11 11 0 0 0 11 -1Z" stroke-width="1"/>'
            '<path d="M0 -1V-11" fill="none" stroke-width="2"/><circle cy="-12" r="2.2" stroke="none"/></g>'
            '<path d="M0 6L-5 13H5Z" stroke-width="1.6"/></g>')


def planet(x, y, r):
    """Small orange planet, lit from the upper left. Returns (defs, svg)."""
    return (rad('pl', [(0, '#ffc07a', 1), (1, '#c8582a', 1)], .35, .35, .7),
            '<circle cx="%s" cy="%s" r="%s" fill="url(#pl)"/>' % (f(x), f(y), f(r)))


def dia_phone(screen):
    """Diamond icon of idevice-control: a white phone with a tap on its screen, on a 46-unit diamond."""
    return ('<rect x="-10" y="-17" width="20" height="34" rx="4.5" fill="#fff" stroke="%s" stroke-width="2.4"/>'
            '<rect x="-6.5" y="-12.5" width="13" height="23" rx="1.5" fill="%s"/>'
            '<circle cx="1" cy="-1" r="7" fill="none" stroke="#fff" stroke-width="1.6" opacity=".8"/>'
            '<circle cx="1" cy="-1" r="3.4" fill="#fff"/>' % (INK, screen))


def dia_pie(_screen):
    """Diamond icon of cc-session-breakdown: a white pie with one slice pulled out, on a 46-unit diamond."""
    return ('<path d="M0 0V-15A15 15 0 1 0 15 0Z" fill="#fff" stroke="%s" stroke-width="2.4" stroke-linejoin="round" '
            'transform="translate(-2 2)"/>'
            '<path d="M0 0V-15A15 15 0 0 1 15 0Z" fill="#fff" stroke="%s" stroke-width="2.4" stroke-linejoin="round" '
            'transform="translate(3 -3)"/>' % (INK, INK))


def diamond(cx, cy, r, icon):
    """Gold diamond with a dark outline, a pale inner line and the project icon. The parts are
    drawn on the first design's 46-unit diamond and scaled to half diagonal r."""
    k = r / 46
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    ri = r - 7 * k
    pin = [(cx, cy - ri), (cx + ri, cy), (cx, cy + ri), (cx - ri, cy)]
    return ('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (poly(pts), DIAMOND, INK, f(3 * k)) +
            '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" opacity=".9"/>'
            % (poly(pin), DIAMOND_LINE, f(2 * k)) +
            '<g transform="%s">%s</g>' % (place(cx, cy, k), icon))


# ---------------------------------------------------------------- effect icons
# Drawn on a 40-unit grid around (0, 0); a token scales them to its radius. Each device is a white
# outline of one stroke weight (DEV_S) on a coloured disc, built from rectangles that are each
# centred on x = 0, so every device is its own mirror image.

DEV_S = 3.0          # bezel width of every device
DISC_R = 20          # coloured base disc, centred on (0, 0) like every device and the pie


def rrect(x, y, w, h, r, fill):
    return ('rect', x, y, w, h, r, fill)


def device_shapes(kind):
    """Shapes (kind, x, y, w, h, rx, fill) of a device, base disc excluded; 'base' = the disc colour."""
    s = DEV_S
    if kind == 'iphone':
        w, h = 15.5, 27
        return [rrect(-w / 2, -h / 2, w, h, 4, '#fff'),
                rrect(-w / 2 + s, -h / 2 + s, w - 2 * s, h - 2 * s, 1.4, 'base'),
                rrect(-2.4, -h / 2 + s + 1.5, 4.8, 1.8, .9, '#fff'),          # dynamic island
                rrect(-2.6, h / 2 - s - 2.3, 5.2, 1, .5, '#fff')]             # home indicator
    if kind == 'ipad':
        w, h = 21.5, 27.5
        return [rrect(-w / 2, -h / 2, w, h, 3, '#fff'),
                rrect(-w / 2 + s, -h / 2 + s, w - 2 * s, h - 2 * s, .9, 'base'),
                rrect(-.65, -h / 2 + s / 2 - .65, 1.3, 1.3, .65, 'base')]     # front camera in the bezel
    if kind == 'tv':
        w, h, top = 31, 20, -13
        return [rrect(-w / 2, top, w, h, 2.6, '#fff'),
                rrect(-w / 2 + s, top + s, w - 2 * s, h - 2 * s, .8, 'base'),
                rrect(-2.6, top + h - .5, 5.2, 3.5, 0, '#fff'),                # neck
                rrect(-7.5, top + h + 3, 15, s, s / 2, '#fff')]                # foot
    raise KeyError(kind)


DEVICE_COLOUR = {'iphone': BLUE, 'ipad': SETI_GREEN, 'tv': RED}
TV_SCREEN_CY = -13 + 10                                      # centre of the TV screen


def play_triangle():
    """Play mark in the TV screen, centred on its centroid, top/bottom symmetric."""
    h = 8.2                                                  # vertical side
    return [(-h * .866 / 3, -h / 2), (h * .866 * 2 / 3, 0), (-h * .866 / 3, h / 2)]


def device_icon(kind):
    base = DEVICE_COLOUR[kind]
    out = ['<circle r="%s" fill="%s"/>' % (f(DISC_R), base)]
    for _, x, y, w, h, r, fill in device_shapes(kind):
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>'
                   % (f(x), f(y), f(w), f(h), f(r), base if fill == 'base' else fill))
    if kind == 'tv':
        pts = [(x, y + TV_SCREEN_CY) for x, y in play_triangle()]
        out.append('<path class="pm" d="%s" fill="#fff" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>' % poly(pts))
    return ''.join(out)


def tok_iphone():
    return device_icon('iphone')


def tok_ipad():
    return device_icon('ipad')


def tok_tv():
    return device_icon('tv')


# Pie chart: four slices from 12 o'clock clockwise, separated by gaps of constant width (PIE_GAP),
# around a small hub. Colours: the SETI resource colours data blue, credit gold, publicity red,
# energy green.
PIE = [(.46, BLUE), (.26, SETI_GOLD), (.17, RED), (.11, SETI_GREEN)]
PIE_R = 19.5
PIE_GAP = 2.2
PIE_HUB = 5


def pie_slice(r, a0, a1, g):
    """Slice between angles a0 and a1 (degrees clockwise from 12 o'clock), its straight edges moved
    in by g/2 so neighbouring slices leave a gap of width g."""
    half = math.radians(a1 - a0) / 2
    mid = math.radians((a0 + a1) / 2 - 90)
    apex = (g / 2) / math.sin(half) if half < math.pi / 2 else g / 2
    da = math.degrees(math.asin((g / 2) / r))
    t0, t1 = math.radians(a0 + da - 90), math.radians(a1 - da - 90)
    ax, ay = apex * math.cos(mid), apex * math.sin(mid)
    large = 1 if (a1 - a0 - 2 * da) > 180 else 0
    return 'M%s %sL%s %sA%s %s 0 %d 1 %s %sZ' % (
        f(ax), f(ay), f(r * math.cos(t0)), f(r * math.sin(t0)), f(r), f(r), large, f(r * math.cos(t1)), f(r * math.sin(t1)))


def tok_pie():
    out, a = [], 0
    for share, colour in PIE:
        out.append('<path d="%s" fill="%s"/>' % (pie_slice(PIE_R, a, a + 360 * share, PIE_GAP), colour))
        a += 360 * share
    out.append('<circle r="%s" fill="#fff"/>' % f(PIE_HUB))
    return ''.join(out)


def token(cx, cy, r, T, icon, gid=''):
    """Flat white reward token: a plain circle with a thin edge, the effect icon (a 27-unit token
    radius on its 40-unit grid) centred on it."""
    return ('<g%s><circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="1"/>'
            % ((' id="%s"' % gid) if gid else '', f(cx), f(cy), f(r), T['tok'], T['tok_line']) +
            '<g transform="%s">%s</g></g>' % (place(cx, cy, r / 27), icon()))


def check_symmetry():
    """Asserts that each device outline is its own mirror image (x -> -x) and that the TV's play
    mark is top/bottom symmetric."""
    def key(s):
        _, x, y, w, h, r, fill = s
        return (round(x, 6), round(y, 6), round(w, 6), round(h, 6), r, fill)
    for kind in DEVICE_COLOUR:
        shapes = device_shapes(kind)
        mirrored = [(k, -x - w, y, w, h, r, fill) for k, x, y, w, h, r, fill in shapes]
        assert sorted(map(key, shapes)) == sorted(map(key, mirrored)), kind + ' not mirror symmetric'
    tri = play_triangle()
    assert sorted((round(x, 6), round(y, 6)) for x, y in tri) == sorted((round(x, 6), round(-y, 6)) for x, y in tri)
    assert abs(sum(x for x, _ in tri)) < 1e-9, 'play mark not centred on its centroid'


# ---------------------------------------------------------------- devices (front views)

def ipad():
    out = ['<rect x="-52" y="-72" width="114" height="152" rx="12" fill="#06080c"/>',
           '<rect x="-57" y="-76" width="114" height="152" rx="12" fill="url(#body)" stroke="url(#rim)" stroke-width="2.2"/>',
           '<rect x="-50" y="-69" width="100" height="138" rx="6" fill="url(#pds)"/>',
           '<rect x="-42" y="-60" width="40" height="40" rx="7" fill="#fff" opacity=".9"/>',
           '<rect x="2" y="-60" width="40" height="40" rx="7" fill="#1b2130" opacity=".55"/>',
           '<path class="chart" d="M-36 -32L-28 -42L-20 -36L-10 -50" fill="none" stroke="#d9583a" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
           '<circle class="load" cx="22" cy="-40" r="11" fill="none" stroke="#ffd36b" stroke-width="3.5" stroke-dasharray="48 30"/>']
    cols = ['#ffd36b', '#ffffff', '#3ba34a', '#2f7fd1', '#e8835c', '#7a5bb5', '#2bb3c9', '#ffffff']
    k = 0
    for row in range(3):
        for col in range(4):
            c = cols[k % 8]
            out.append('<rect x="%d" y="%d" width="15" height="15" rx="4" fill="%s" opacity="%g"/>'
                       % (-42 + col * 23, -10 + row * 22, c, .75 if c == '#ffffff' else .92))
            k += 1
    out.append('<rect x="-38" y="56" width="76" height="9" rx="4.5" fill="#fff" opacity=".22"/>')
    out.append('<path d="M-50 -63A6 6 0 0 1 -44 -69H8L-50 6Z" fill="url(#glass)"/>')
    return ''.join(out)


def apple_tv_front():
    """Apple TV box seen from the front: a low rounded slab with a lit top face and a status light."""
    return ('<rect x="-40" y="-13" width="80" height="26" rx="7" fill="url(#tvb)" stroke="#4a505e" stroke-width="1.4"/>'
            '<rect x="-36" y="-11.5" width="72" height="5" rx="2.5" fill="#fff" opacity=".16"/>'
            '<rect x="-34" y="-9" width="68" height="1.4" rx=".7" fill="#fff" opacity=".3"/>'
            '<circle cx="30" cy="4" r="6" fill="#7dffb0" opacity=".3" filter="url(#b2)"/>'
            '<circle class="led" cx="30" cy="4" r="2.6" fill="#7dffb0"/>')


def remote():
    return ('<rect x="-14" y="-50" width="28" height="100" rx="12" fill="url(#alu)" stroke="#5f6670" stroke-width="1.2"/>'
            '<rect x="-10" y="-46" width="5" height="90" rx="2.5" fill="#fff" opacity=".35"/>'
            '<circle cy="-29" r="11" fill="#17191d"/><circle cy="-29" r="5.5" fill="none" stroke="#3a3e46" stroke-width="1.4"/>'
            '<circle class="press" cy="-29" r="3.2" fill="#6fe0ff"/>'
            '<circle cx="-5.5" cy="-7" r="3.6" fill="#17191d"/><circle cx="5.5" cy="-7" r="3.6" fill="#17191d"/>'
            '<circle cx="-5.5" cy="4" r="3.6" fill="#17191d"/><circle cx="5.5" cy="4" r="3.6" fill="#17191d"/>'
            '<rect x="-3.2" y="13" width="6.4" height="18" rx="3.2" fill="#17191d"/>')


def iphone():
    out = ['<rect x="-42" y="-90" width="94" height="188" rx="18" fill="#06080c"/>',
           '<rect x="-47" y="-94" width="94" height="188" rx="18" fill="url(#body)" stroke="url(#rim)" stroke-width="2.4"/>',
           '<rect x="-49.5" y="-50" width="2.5" height="20" rx="1" fill="#8b95ad"/>',
           '<rect x="47" y="-40" width="2.5" height="30" rx="1" fill="#8b95ad"/>',
           '<rect x="-41" y="-88" width="82" height="176" rx="13" fill="url(#phs)"/>',
           '<rect x="-14" y="-83" width="28" height="8.5" rx="4.25" fill="#05070b"/>']
    pcols = ['#ffd36b', '#3ba34a', '#ffffff', '#e8835c', '#2bb3c9', '#ffffff', '#7a5bb5', '#f2c14e',
             '#3ba34a', '#ffffff', '#d9442c', '#2bb3c9', '#ffffff', '#ffd36b', '#2f7fd1', '#e8835c']
    k = 0
    for row in range(4):
        for col in range(4):
            out.append('<rect x="%.1f" y="%d" width="14" height="14" rx="4" fill="%s" opacity="%g"/>'
                       % (-33 + col * 18.5, -64 + row * 22, pcols[k], .8 if pcols[k] == '#ffffff' else .95))
            k += 1
    out.append('<rect x="-35" y="50" width="70" height="26" rx="10" fill="#fff" opacity=".2"/>')
    for col in range(4):
        out.append('<rect x="%.1f" y="56" width="14" height="14" rx="4" fill="%s"/>'
                   % (-31 + col * 17, ('#3ba34a', '#2f7fd1', '#ffffff', '#ffd36b')[col]))
    out.append('<rect x="-15" y="81" width="30" height="3" rx="1.5" fill="#fff" opacity=".75"/>')
    out.append('<path d="M-41 -75A13 13 0 0 1 -28 -88H20L-41 10Z" fill="url(#glass)"/>')
    # a finger tap that hops between three apps
    for i, (col, row) in enumerate(((2, 1), (0, 2), (3, 0))):
        tx, ty = -33 + col * 18.5 + 7, -64 + row * 22 + 7
        out.append('<g transform="translate(%.1f %d)"><g class="tap tp%d">'
                   '<circle class="rip" r="11" fill="none" stroke="#fff" stroke-width="2.8"/>'
                   '<circle r="10" fill="#fff" opacity=".3"/><circle r="5.5" fill="#fff"/></g></g>' % (tx, ty, i))
    return ''.join(out)


def ridge_pts(seed, x0, x1, base, amp, step):
    rnd = random.Random(seed)
    p, x = [], x0
    while x < x1:
        p.append((x, base - amp * rnd.uniform(.35, 1.0)))
        x += step * rnd.uniform(.6, 1.3)
    p.append((x1, base - amp * rnd.uniform(.35, 1.0)))
    return p


def ridge(seed, x0, x1, base, amp, step, fill, rim=None, op=1.0):
    """Mountain silhouette filled down to `base`; rim: (colour, opacity) of light along its crest."""
    p = ridge_pts(seed, x0, x1, base, amp, step)
    d = 'M%s %s' % (f(x0), f(base)) + ''.join('L%s %s' % (f(a), f(b)) for a, b in p) + 'L%s %sZ' % (f(x1), f(base))
    out = '<path d="%s" fill="%s"%s/>' % (d, fill, (' opacity="%g"' % op) if op < 1 else '')
    if rim:
        out += ('<path d="M%s" fill="none" stroke="%s" stroke-opacity="%s" stroke-width=".9" stroke-linejoin="round"/>'
                % ('L'.join('%s %s' % (f(a), f(b + .5)) for a, b in p), rim[0], f(rim[1])))
    return out


def rocks(seed, n, x0, x1, y0, y1, fill, size=(3, 8), rim=None):
    rnd = random.Random(seed)
    body, tops = [], []
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        w = rnd.uniform(*size)
        h = w * rnd.uniform(.35, .6)
        body.append('M%s %sQ%s %s %s %sQ%s %s %s %sZ' % (f(x - w), f(y), f(x - w * .4), f(y - h * 1.6), f(x + w * .2), f(y - h),
                                                       f(x + w * .7), f(y - h * .8), f(x + w), f(y)))
        tops.append('M%s %sQ%s %s %s %s' % (f(x - w * .7), f(y - h * .5), f(x - w * .35), f(y - h * 1.3), f(x + w * .2), f(y - h)))
    out = '<path d="%s" fill="%s"/>' % (''.join(body), fill)
    if rim:
        out += '<path d="%s" fill="none" stroke="%s" stroke-opacity=".55" stroke-width=".8" stroke-linecap="round"/>' % (''.join(tops), rim)
    return out


def outpost(x, y, s, fill, lit='#ffd27a'):
    """Distant outpost on the horizon: two domes, a hall with lit windows and a mast with a beacon."""
    return ('<g transform="translate(%s %s) scale(%s)" fill="%s">'
            '<path d="M-14 0A8 8 0 0 1 2 0Z"/><path d="M3 0A5 5 0 0 1 13 0Z"/>'
            '<rect x="14" y="-5" width="16" height="5"/><rect x="34" y="-17" width="1.4" height="17"/></g>'
            '<g transform="translate(%s %s) scale(%s)" fill="%s"><rect x="16.5" y="-3.6" width="2.4" height="1.6"/>'
            '<rect x="21" y="-3.6" width="2.4" height="1.6"/><rect x="25.5" y="-3.6" width="2.4" height="1.6"/>'
            '<circle cx="34.7" cy="-17.5" r="4" fill="#ff6b5a" opacity=".3" filter="url(#b1)"/>'
            '<circle class="beacon" cx="34.7" cy="-17.5" r="1.6" fill="#ff6b5a"/></g>'
            % (f(x), f(y), f(s), fill, f(x), f(y), f(s), lit))


def nebula(clouds):
    """Soft painted haze in the sky: blurred ellipses (cx, cy, rx, ry, colour, opacity)."""
    return '<g filter="url(#b8)">%s</g>' % ''.join(
        '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" opacity="%s"/>' % (f(x), f(y), f(a), f(b), c, f(o))
        for x, y, a, b, c, o in clouds)


def cirrus(w, hz, sw, col):
    """Thin cloud streaks low in the sky, lit from below by the glow on the horizon."""
    rows = ((.12, -40, .9, .35), (.55, -33, 1.2, .3), (.3, -24, .8, .4), (.78, -20, .7, .35))
    return '<g filter="url(#b1)">%s</g>' % ''.join(
        '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" opacity="%s"/>' % (f(w * x), f(hz + dy * sw), f(60 * k * sw + 10), f(1.6 * sw + .4), col, f(o))
        for x, dy, k, o in rows)


def moon(mx, my, mr, uid):
    """Lit sphere: radial shading, soft terminator, craters with a lit rim, and a halo."""
    defs = (rad(uid + 'h', [(0, '#fff3d6', .55), (.45, '#ffe2b0', .18), (1, '#ffe2b0', 0)]) +
            rad(uid + 's', [(0, '#fffaf0', 1), (.55, '#f2dfbb', 1), (1, '#b9986e', 1)], .38, .34, .7) +
            lin(uid + 't', [(0, '#2a2347', 0), (.55, '#2a2347', 0), (1, '#2a2347', .75)], 0, 0, 1, .4) +
            '<clipPath id="%sc"><circle cx="%s" cy="%s" r="%s"/></clipPath>' % (uid, f(mx), f(my), f(mr)))
    cr = ''.join('<circle cx="%s" cy="%s" r="%s" fill="#c9ad84" opacity=".7"/>'
                 '<path d="M%s %sA%s %s 0 0 0 %s %s" fill="none" stroke="#fff8e8" stroke-width="%s" opacity=".7"/>'
                 % (f(mx + dx * mr), f(my + dy * mr), f(rr * mr), f(mx + dx * mr - rr * mr), f(my + dy * mr),
                    f(rr * mr), f(rr * mr), f(mx + dx * mr + rr * mr), f(my + dy * mr), f(max(.5, mr * .04)))
                 for dx, dy, rr in ((-.35, -.25, .18), (-.05, .42, .13), (.3, -.1, .1), (-.5, .25, .08)))
    svg = ('<circle cx="%s" cy="%s" r="%s" fill="url(#%sh)"/>' % (f(mx), f(my), f(mr * 2.6), uid) +
           '<circle cx="%s" cy="%s" r="%s" fill="url(#%ss)"/>' % (f(mx), f(my), f(mr), uid) +
           '<g clip-path="url(#%sc)">%s<rect x="%s" y="%s" width="%s" height="%s" fill="url(#%st)"/></g>'
           % (uid, cr, f(mx - mr), f(my - mr), f(2 * mr), f(2 * mr), uid))
    return defs, svg


def vignette(w, h, op=.4):
    return ('<rect width="%s" height="%s" fill="url(#vig)" opacity="%s"/>' % (f(w), f(h), f(op)),
            rad('vig', [(0, '#000', 0), (.65, '#000', 0), (1, '#000', 1)], .5, .45, .75))


# ---------------------------------------------------------------- art: idevice-control
# Dusk on a quiet plain: devices stand on the ground like buildings of an outpost, linked by
# data streams; a moon and a satellite in the sky, hazy mountain ridges, a glowing horizon.

ART_IDEVICE = {
    'wide': dict(w=262, h=180, hz=134, moon=(104, 38, 12), sat=26,
                 ipad=(70, 116, .47), phone=(144, 105, .53), tv=(204, 150, .52), remote=(239, 133, .43),
                 star_n=40, ridge_amp=(30, 22, 13)),
    'phone': dict(w=293, h=88, hz=64, moon=(214, 18, 8), sat=10,
                  ipad=(98, 47, .29), phone=(150, 42, .32), tv=(206, 70, .34), remote=(244, 57, .27),
                  star_n=30, ridge_amp=(17, 12, 7)),
}


def art_idevice(v):
    a = ART_IDEVICE[v]
    w, h, hz = a['w'], a['h'], a['hz']
    ix, iy, isc = a['ipad']
    px, py, ps = a['phone']
    tx, ty, tsc = a['tv']
    rx, ry, rsc = a['remote']
    mx, my, mr = a['moon']
    wide = v == 'wide'
    mdefs, msvg = moon(mx, my, mr, 'mn')
    vsvg, vdefs = vignette(w, h)
    defs = (
        lin('sky', [(0, '#08112b', 1), (.42, '#1b3670', 1), (.74, '#5a4e98', 1), (.9, '#cf7a78', 1), (1, '#f6ab68', 1)],
            0, 0, 0, hz, True) +
        lin('gnd', [(0, '#3a2c5e', 1), (.3, '#271f48', 1), (1, '#110d22', 1)], 0, hz, 0, h, True) +
        lin('rg1', [(0, '#9a7fc0', 1), (1, '#6d5aa5', 1)], 0, hz - a['ridge_amp'][0], 0, hz, True) +
        lin('rg2', [(0, '#5e4c95', 1), (1, '#3f3373', 1)], 0, hz - a['ridge_amp'][1], 0, hz, True) +
        lin('rg3', [(0, '#3a2e66', 1), (1, '#251d47', 1)], 0, hz - a['ridge_amp'][2], 0, hz, True) +
        lin('haze', [(0, '#f6a98a', 0), (.6, '#f6a98a', .35), (1, '#ffd0a0', 0)], 0, 0, 0, 1) +
        rad('hglow', [(0, '#ffd09a', .85), (.4, '#ffb27a', .4), (1, '#ffb27a', 0)]) +
        rad('pool', [(0, '#8fc2ff', .5), (1, '#8fc2ff', 0)]) +
        rad('poolo', [(0, '#ffb07a', .4), (1, '#ffb07a', 0)]) +
        lin('fog', [(0, '#9d8ee0', 0), (.5, '#9d8ee0', .32), (1, '#9d8ee0', 0)], 0, 0, 0, 1) +
        lin('phs', [(0, '#3aa0e8', 1), (.55, '#4a63d0', 1), (1, '#7a4cc0', 1)], 0, 0, .4, 1) +
        lin('pds', [(0, '#f3a64a', 1), (.6, '#d9583a', 1), (1, '#7c2f5c', 1)], 0, 0, .3, 1) +
        lin('alu', [(0, '#8d949e', 1), (.4, '#eef0f3', 1), (1, '#a4aab3', 1)], 0, 0, 1, 0) +
        lin('body', [(0, '#3c4558', 1), (.5, '#151a24', 1), (1, '#0a0d13', 1)], 0, 0, .25, 1) +
        lin('rim', [(0, '#c9d6f0', 1), (.25, '#4a5263', 1), (.75, '#4a5263', 1), (1, '#ffc9a0', 1)], 0, 0, 1, 0) +
        lin('glass', [(0, '#fff', .28), (1, '#fff', 0)], 0, 0, 1, 1) +
        lin('tvb', [(0, '#3a3f4c', 1), (.5, '#1a1d24', 1), (1, '#0d0f14', 1)], 0, 0, 0, 1) +
        mdefs + vdefs
    )
    avoid = [(px, py, 60 * ps / .53), (ix, iy, 40 * isc / .47), (mx, my, mr + 8)]
    clouds = ([(60, 26, 70, 18, '#4fa3d9', .32), (210, 46, 80, 22, '#b34fa8', .3), (140, 92, 120, 16, '#f08a6a', .26),
               (30, 70, 50, 12, '#7f6fd8', .3), (250, 12, 50, 14, '#3f8fd0', .25)]
              if wide else [(70, 14, 80, 10, '#4fa3d9', .32), (230, 26, 80, 12, '#b34fa8', .3), (150, 48, 140, 9, '#f08a6a', .26)])
    sw = 1 if wide else .6
    out = ['<rect width="%s" height="%s" fill="url(#sky)"/>' % (f(w), f(hz + 1)),
           nebula(clouds),
           stars(11, a['star_n'], avoid, 0, 0, w, hz * .7, 1.0 if wide else .8),
           msvg,
           # satellite drifting across the sky
           '<g class="sat"><g transform="translate(-20 %s)"><circle r="5" fill="#cfe0ff" opacity=".18" filter="url(#b1)"/>'
           '<rect x="-1.6" y="-1.2" width="3.2" height="2.4" fill="#e8eef8"/>'
           '<rect x="-6.5" y="-.6" width="4.2" height="1.2" fill="#8fb4ff"/><rect x="2.3" y="-.6" width="4.2" height="1.2" fill="#8fb4ff"/>'
           '</g></g>' % f(a['sat']),
           '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="url(#hglow)"/>' % (f(px), f(hz), f(w * .62), f(hz * .55)),
           cirrus(w, hz, sw, '#ffc2a8'),
           ridge(2, -4, w + 4, hz + 1, a['ridge_amp'][0], 26 if wide else 30, 'url(#rg1)', ('#ffd8c0', .6), .85),
           '<rect y="%s" width="%s" height="%s" fill="url(#haze)" filter="url(#b2)"/>' % (f(hz - 16 * sw), f(w), f(16 * sw)),
           ridge(3, -4, w + 4, hz + 1, a['ridge_amp'][1], 18 if wide else 22, 'url(#rg2)', ('#ffb894', .55)),
           ridge(8, -4, w + 4, hz + 2, a['ridge_amp'][2], 12 if wide else 16, 'url(#rg3)', ('#ff9f7a', .45)),
           '<rect y="%s" width="%s" height="%s" fill="url(#gnd)"/>' % (f(hz + 1), f(w), f(h - hz)),
           '<rect y="%s" width="%s" height="1.6" fill="#ffc48a" opacity=".55" filter="url(#b1)"/>' % (f(hz + .5), f(w)),
           outpost(18 if wide else 36, hz + 2, .9 if wide else .6, '#241d45'),
           outpost(178 if wide else 232, hz + 2, .7 if wide else .5, '#241d45'),
           '<g fill="#4a3d82" opacity=".6">%s</g>' % ''.join(
               '<rect x="%s" y="%s" width="%s" height="1.1" rx=".55"/>' % (f(x), f(y), f(wd))
               for x, y, wd in random.Random(4).sample([(rx_, hz + 4 + (h - hz) * k / 6, 20 + 30 * (k % 3))
                                                        for k in range(1, 6) for rx_ in (10, 90, 170, 230)], 10)),
           ]
    # light pools and soft contact shadows on the ground
    gy = hz + (21 if wide else 11)
    out.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="url(#pool)"/>' % (f(px), f(gy), f(w * .32), f((h - hz) * .5)))
    out.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="url(#poolo)"/>' % (f(ix), f(gy), f(w * .2), f((h - hz) * .4)))
    out.append('<g filter="url(#b1)">%s</g>' % ''.join(
        '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#07050f" opacity=".7"/>' % (f(x + 2), f(gy + .5), f(half), f(max(1.4, half * .14)))
        for x, half in ((ix, 30 * isc / .47), (px, 28 * ps / .53), (tx, 24 * tsc / .52), (rx, 8 * rsc / .43))))
    # screen glow behind the iPad and the iPhone
    out.append('<g filter="url(#b8)"><rect x="%s" y="%s" width="%s" height="%s" rx="8" fill="#ff9a5a" opacity=".7"/>'
               '<rect x="%s" y="%s" width="%s" height="%s" rx="10" fill="#5a86ff" opacity=".8"/></g>'
               % (f(ix - 52 * isc), f(iy - 70 * isc), f(104 * isc), f(140 * isc),
                  f(px - 44 * ps), f(py - 90 * ps), f(88 * ps), f(180 * ps)))
    # data streams from the phone to the other devices
    flows = [(px - 26 * ps / .53, py + 10 * ps / .53, ix + 28 * isc / .47, iy - 6 * isc / .47),
             (px + 26 * ps / .53, py + 18 * ps / .53, tx - 18 * tsc / .52, ty - 8 * tsc / .52),
             (px + 26 * ps / .53, py - 10 * ps / .53, rx - 6 * rsc / .43, ry - 18 * rsc / .43)]
    glow, core = [], []
    for x0, y0, x1, y1 in flows:
        cx_, cy_ = (x0 + x1) / 2, min(y0, y1) - 12 * (1 if wide else .5)
        d = 'M%s %sQ%s %s %s %s' % (f(x0), f(y0), f(cx_), f(cy_), f(x1), f(y1))
        glow.append('<path d="%s"/>' % d)
        core.append('<path class="flow" d="%s"/>' % d)
    out.append('<g fill="none" stroke="#7fe3ff" stroke-width="3.2" opacity=".3" filter="url(#b1)">%s</g>' % ''.join(glow))
    out.append('<g fill="none" stroke="#bff3ff" stroke-width="1.8" stroke-linecap="round" stroke-dasharray=".8 4.6">%s</g>' % ''.join(core))
    # the iPad on a stand, the iPhone, the Apple TV box and the remote
    stand_top = iy + 76 * isc
    out.append('<path d="M%s %sL%s %sH%sL%s %sZ" fill="url(#body)"/>' % (
        f(ix - 4), f(stand_top - 1), f(ix - 10), f(gy), f(ix + 10), f(ix + 4), f(stand_top - 1)))
    out.append('<g transform="%s">%s</g>' % (place(ix, iy, isc), ipad()))
    out.append('<g transform="%s">%s</g>' % (place(px, py, ps), iphone()))
    out.append('<g transform="%s">%s</g>' % (place(tx, ty, tsc), apple_tv_front()))
    out.append('<g transform="%s">%s</g>' % (place(rx, ry, rsc), remote()))
    # radio rings rising from the phone
    out.append('<g transform="translate(%s %s)" fill="none" stroke="#bfe9ff" stroke-width="1.6" stroke-linecap="round">'
               '<path class="ring" d="M-9 -2A12 12 0 0 1 9 -2"/><path class="ring r2" d="M-9 -2A12 12 0 0 1 9 -2"/></g>'
               % (f(px), f(py - 94 * ps - 3)))
    # low ground fog over the device feet, foreground rocks with a lit crest, grain and a vignette
    out.append('<rect y="%s" width="%s" height="%s" fill="url(#fog)" filter="url(#b2)"/>' % (f(gy - 9 * sw), f(w), f(16 * sw)))
    out.append(rocks(21, 9 if wide else 7, 60, w, h - 9, h + 1, '#0d0a1c', (4, 11) if wide else (3, 7), '#8b78c8'))
    out.append(grain(w, h))
    out.append(vsvg)
    style = (
        '.sat{animation:sat 16s linear infinite}'
        '@keyframes sat{from{transform:translateX(0)}to{transform:translateX(%spx)}}' % f(w + 40) +
        '.tap{opacity:0;animation:tap 4.5s ease-out infinite}.tp0{opacity:1}'
        '.tp1{animation-delay:1.5s}.tp2{animation-delay:3s}'
        '@keyframes tap{0%{opacity:0}4%{opacity:1}30%{opacity:1}36%,100%{opacity:0}}'
        '.rip{transform-box:fill-box;transform-origin:center;animation:rip 1.5s ease-out infinite}'
        '@keyframes rip{0%{transform:scale(.45);opacity:.95}100%{transform:scale(2.2);opacity:0}}'
        '.flow{animation:flow 1.2s linear infinite}'
        '@keyframes flow{to{stroke-dashoffset:-10.8}}'
        '.led,.press{animation:blink 1.5s ease-in-out infinite}'
        '@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}'
        '.ring{transform-box:fill-box;transform-origin:center bottom;opacity:0;animation:ring 2.4s ease-out infinite}'
        '.r2{animation-delay:1.2s}'
        '@keyframes ring{0%{transform:translateY(0) scale(.6);opacity:.9}100%{transform:translateY(-10px) scale(1.7);opacity:0}}'
        '.load{transform-box:fill-box;transform-origin:center;animation:load 2s linear infinite}'
        '.beacon{animation:blink 2s ease-in-out infinite}'
        '@keyframes load{to{transform:rotate(360deg)}}'
    )
    return defs, ''.join(out), style


# ---------------------------------------------------------------- art: cc-session-breakdown
# Night over a plain: the usage ring rises behind the hills like a giant moon; an observatory and
# its dish send a stream of data tokens up to it.

ART_CCSB = {
    'wide': dict(w=262, h=180, hz=138, c=(146, 95), s=.5, obs=(80, 142), coin=(.5, (100, 128), (30, -52)),
                 star_n=40, ridge_amp=(26, 20, 12)),
    'phone': dict(w=293, h=88, hz=66, c=(196, 42), s=.29, obs=(96, 68), coin=(.34, (112, 60), (40, -30)),
                  star_n=30, ridge_amp=(15, 11, 7)),
}

RINGS = [  # inner radius, outer radius, parts (share, colour), start angle, class
    (84, 110, [(49, '#2bb3c9'), (16, '#f2c14e'), (15, '#e0523a'), (10, '#8a66c9'), (5, '#3fae52'), (4, '#3a86dc'), (1, '#b7bfcc')], -20, 'spin'),
    (60, 82, [(40, '#e08a4f'), (25, '#b9592f'), (20, '#f3b47c'), (15, '#8c4426')], 30, 'spin2'),
    (38, 58, [(60, '#f6c75a'), (25, '#e9973a'), (15, '#fde7a8')], 70, ''),
]


def ring_defs():
    """Tube shading for each usage ring (dark edges, light crest) and a light from the upper left."""
    out = []
    for i, (r0, r1, *_rest) in enumerate(RINGS):
        a, b = r0 / r1, (r0 + r1) / 2 / r1
        out.append(rad('tube%d' % i, [(0, '#000', .45), (a, '#000', .38), ((a + b) / 2, '#fff', .05), (b, '#fff', .32),
                                      ((b + 1) / 2, '#000', 0), (1, '#000', .45)], 0, 0, r1, user=True))
    out.append(lin('rlight', [(0, '#fff', .32), (.45, '#fff', 0), (.6, '#000', 0), (1, '#000', .45)], -128, -128, 128, 128, True))
    out.append(rad('rback', [(0, '#1b2b5c', 1), (1, '#0a1230', 1)], 0, 0, 128, user=True))
    return ''.join(out)


def ring_chart():
    """Score ring, three usage rings and the sun, around (0, 0), in 420-card units (outer radius 128)."""
    out = ['<circle r="168" fill="none" stroke="#c9b8ff" stroke-opacity=".25" stroke-width="1.6" stroke-dasharray="3 9"/>',
           '<circle r="122" fill="url(#rback)" stroke="#1d63c4" stroke-width="12"/>',
           '<circle r="128" fill="none" stroke="#9cc8ff" stroke-width="1.4" opacity=".8"/>']
    ticks = []
    for i in range(48):
        t = math.radians(i * 7.5)
        r0, r1 = (117.5, 126.5) if i % 4 == 0 else (119.5, 124.5)
        ticks.append('M%.1f %.1fL%.1f %.1f' % (r0 * math.sin(t), -r0 * math.cos(t), r1 * math.sin(t), -r1 * math.cos(t)))
    out.append('<path class="bezel" d="%s" stroke="#cfe4ff" stroke-width="1.4" opacity=".75"/>' % ''.join(ticks))
    for i, (r0, r1, parts, start, cls) in enumerate(RINGS):
        segs, ang = [], start
        tot = sum(p for p, _ in parts)
        for j, (p, col) in enumerate(parts):
            span = 360 * p / tot
            segs.append('<path d="%s" fill="%s"%s/>' % (annulus(r0, r1, ang, ang + span), col,
                                                         ' class="hot"' if (cls == 'spin' and j == 0) else ''))
            ang += span
        out.append('<g stroke="#140f30" stroke-width="2.6" stroke-linejoin="round"%s>%s</g>' % (
            (' class="%s"' % cls) if cls else '', ''.join(segs)))
        out.append('<path d="%s" fill="url(#tube%d)"/>' % (annulus(r0, r1, 0, 359.99), i))
    out.append('<circle r="128" fill="url(#rlight)"/>')
    # specular arc on the bezel, upper left
    out.append('<path d="M-118 -30A122 122 0 0 1 -30 -118" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".45"/>')
    out.append('<circle class="halo" r="54" fill="url(#halo)"/>')
    out.append('<circle r="44" fill="#ffd36b" opacity=".6" filter="url(#b8)"/>')
    out.append('<circle r="30" fill="url(#sun)" stroke="#b8561a" stroke-width="1.5"/>')
    out.append('<ellipse cx="-9" cy="-11" rx="10" ry="7" fill="#fff" opacity=".55" filter="url(#b2)"/>')
    return ''.join(out)


def observatory(s):
    """Domed observatory with a lit slit and windows, and a small dish beside it; base centre at (0, 0)."""
    return ('<g transform="scale(%s)">'
            '<rect x="-22" y="-14" width="44" height="14" fill="url(#owall)"/>'
            '<path d="M-20 -14A20 20 0 0 1 20 -14Z" fill="url(#odome)"/>'
            '<path d="M14 -24A20 20 0 0 1 20 -14" fill="none" stroke="#ffe7b8" stroke-width="1.6" opacity=".9"/>'
            '<path d="M-3 -33.5L3 -33.5L3.5 -14H-3.5Z" fill="#2a1f45"/>'
            '<path d="M-2 -32L2 -32L2.4 -15H-2.4Z" fill="#ffd27a" opacity=".35"/>'
            '<path class="scope" d="M-1.5 -22L8 -40" stroke="#ffd27a" stroke-width="2.4" stroke-linecap="round" opacity=".8"/>'
            '<g fill="#ffd27a"><rect x="-15" y="-9" width="5" height="4" rx="1"/><rect x="-6" y="-9" width="5" height="4" rx="1"/>'
            '<rect x="10" y="-9" width="5" height="4" rx="1"/></g>'
            '<g transform="translate(36 -2)"><path d="M-2 0L0 -14L2 0Z" fill="#8a80a8"/>'
            '<g transform="translate(0 -16) rotate(-30)"><path d="M-11 -2A11 11 0 0 0 11 -2Z" fill="url(#odome)"/>'
            '<path d="M0 -2V-12" stroke="#c9c2dc" stroke-width="1.4"/><circle cy="-12.5" r="1.8" fill="#e8e2f4"/></g></g>'
            '</g>' % f(s))


def glyph_dish(color):
    """Radio dish silhouette, side view, aimed up-right: bowl, feed arm, stand."""
    return ('<g fill="%s"><g transform="rotate(35)"><path d="M-9 -2A9 9 0 0 0 9 -2Z"/>'
            '<path d="M-.7 -2V-9H.7V-2Z"/><circle cy="-9.6" r="1.9"/></g>'
            '<path d="M-1.4 4L-5 10.5H5L1.4 4Z"/></g>' % color)


def art_ccsb(v):
    a = ART_CCSB[v]
    w, h, hz = a['w'], a['h'], a['hz']
    cx, cy = a['c']
    s = a['s']
    ox, oy = a['obs']
    csc, (x0, y0), (dx, dy) = a['coin']
    wide = v == 'wide'
    dish_xs, dsc = ((176, 197, 218, 239), .55) if wide else ((236, 254, 272), .38)
    vsvg, vdefs = vignette(w, h)
    defs = (
        lin('sky', [(0, '#0a0824', 1), (.48, '#291c5c', 1), (.8, '#7a3b7e', 1), (.94, '#dc7369', 1), (1, '#f3a75c', 1)],
            0, 0, 0, hz, True) +
        lin('gnd', [(0, '#35255a', 1), (.3, '#24193f', 1), (1, '#110b20', 1)], 0, hz, 0, h, True) +
        lin('rg1', [(0, '#8f5c9e', 1), (1, '#5f3f7c', 1)], 0, hz - a['ridge_amp'][0], 0, hz, True) +
        lin('rg2', [(0, '#4f3678', 1), (1, '#36265e', 1)], 0, hz - a['ridge_amp'][1], 0, hz, True) +
        lin('rg3', [(0, '#33245a', 1), (1, '#221640', 1)], 0, hz - a['ridge_amp'][2], 0, hz, True) +
        lin('haze', [(0, '#f29a7a', 0), (.6, '#f29a7a', .3), (1, '#ffc38a', 0)], 0, 0, 0, 1) +
        lin('fog', [(0, '#b48ad8', 0), (.5, '#b48ad8', .3), (1, '#b48ad8', 0)], 0, 0, 0, 1) +
        rad('gglow', [(0, '#ffb35a', .45), (1, '#ffb35a', 0)]) +
        rad('rglow', [(.4, '#ffb648', .42), (1, '#ffb648', 0)], cx, cy, 128 * s * 1.7, user=True) +
        rad('sun', [(0, '#fff8d2', 1), (.45, '#ffcf55', 1), (1, '#ee8424', 1)], .42, .4, .65) +
        rad('halo', [(.5, '#ffb648', .55), (1, '#ffb648', 0)]) +
        lin('odome', [(0, '#8d85ab', 1), (.6, '#d9d2ea', 1), (1, '#fff3dc', 1)], 0, 0, 1, 0) +
        lin('owall', [(0, '#2c2249', 1), (1, '#4a3c74', 1)], 0, 0, 1, 0) +
        rad('coing', [(0, '#7fe6ff', 1), (.6, '#1aa3c9', 1), (1, '#0d6f8f', 1)], .38, .32, .7) +
        '<g id="coin"><circle r="14" fill="#5fe0ff" opacity=".25"/>'
        '<circle r="10.5" fill="url(#coing)" stroke="#0e121a" stroke-width="1.6"/>'
        '<circle r="7.5" fill="none" stroke="#c4f4ff" stroke-width="1.2" opacity=".8"/>'
        '<path d="M-4.5 -3.6h2v2h-2zM-1 -3.6h2v2h-2zM2.5 -3.6h2v2h-2zM-4.5 0h2v2h-2zM2.5 0h2v2h-2zM-1 3.6h2v-2h-2z" fill="#e9fbff"/></g>' +
        ring_defs() + vdefs
    )
    clouds = ([(50, 30, 70, 20, '#5a7fe0', .3), (220, 30, 70, 20, '#c05ab0', .28), (150, 112, 140, 14, '#f2906a', .28),
               (30, 80, 50, 14, '#8a5ad0', .28)]
              if wide else [(60, 14, 80, 10, '#5a7fe0', .3), (270, 16, 60, 10, '#c05ab0', .28), (150, 54, 150, 8, '#f2906a', .28)])
    sw = 1 if wide else .6
    out = ['<rect width="%s" height="%s" fill="url(#sky)"/>' % (f(w), f(hz + 1)),
           nebula(clouds),
           stars(23, a['star_n'], [(cx, cy, 136 * s)], 0, 0, w, hz * .8, 1.0 if wide else .8),
           '<circle cx="%s" cy="%s" r="%s" fill="url(#rglow)"/>' % (f(cx), f(cy), f(128 * s * 1.7)),
           '<g transform="%s">%s</g>' % (place(cx, cy, s), ring_chart()),
           cirrus(w, hz, sw, '#ffb8a0'),
           ridge(4, -4, w + 4, hz + 1, a['ridge_amp'][0], 24 if wide else 28, 'url(#rg1)', ('#ffc9a0', .6), .85),
           '<rect y="%s" width="%s" height="%s" fill="url(#haze)" filter="url(#b2)"/>' % (f(hz - 15 * sw), f(w), f(15 * sw)),
           ridge(5, -4, w + 4, hz + 1, a['ridge_amp'][1], 16 if wide else 20, 'url(#rg2)', ('#ffb37a', .55)),
           ridge(9, -4, w + 4, hz + 2, a['ridge_amp'][2], 11 if wide else 15, 'url(#rg3)', ('#ff9a6a', .45)),
           '<rect y="%s" width="%s" height="%s" fill="url(#gnd)"/>' % (f(hz + 1), f(w), f(h - hz)),
           '<rect y="%s" width="%s" height="1.6" fill="#ffc48a" opacity=".5" filter="url(#b1)"/>' % (f(hz + .5), f(w)),
           '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="url(#gglow)"/>' % (f(cx), f(hz + 4 * sw), f(80 * sw + 20), f(12 * sw)),
           ''.join('<g transform="translate(%s %s) scale(%s)">%s</g>' % (f(x), f(hz - 9 * dsc), f(dsc), glyph_dish('#1f1638'))
                   for x in dish_xs),
           outpost(14 if wide else 40, hz + 2, .8 if wide else .5, '#1f1638'),
           '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#07050f" opacity=".6" filter="url(#b1)"/>'
           % (f(ox + 4 * sw), f(oy + 1), f(30 * sw), f(2.2 * sw)),
           '<g transform="translate(%s %s)">%s</g>' % (f(ox), f(oy), observatory(1 if wide else .6)),
           '<path d="M%s %sl%s %s" stroke="#7fdcff" stroke-width="2.6" opacity=".25" filter="url(#b1)"/>' % (f(x0), f(y0), f(dx), f(dy)),
           '<path d="M%s %sl%s %s" stroke="#bff0ff" stroke-width="1" stroke-dasharray=".8 4" '
           'stroke-linecap="round" opacity=".7"/>' % (f(x0), f(y0), f(dx), f(dy))]
    for i in range(4):
        out.append('<g transform="translate(%s %s)"><use href="#coin" transform="translate(%s %s) scale(%s)" class="coin" '
                   'style="animation-delay:-%gs"/></g>' % (f(x0), f(y0), f(dx * i / 4), f(dy * i / 4), f(csc), i * 1.5))
    out.append('<rect y="%s" width="%s" height="%s" fill="url(#fog)" filter="url(#b2)"/>' % (f(hz + 2 * sw), f(w), f(14 * sw)))
    out.append(rocks(31, 8 if wide else 6, 60, w, h - 9, h + 1, '#0c0818', (4, 11) if wide else (3, 7), '#c08a9a'))
    out.append(grain(w, h))
    out.append(vsvg)
    style = (
        '.spin{transform-box:fill-box;transform-origin:center;animation:spin 36s linear infinite}'
        '.spin2{transform-box:fill-box;transform-origin:center;animation:spin 60s linear infinite reverse}'
        '.bezel{transform-box:fill-box;transform-origin:center;animation:spin 90s linear infinite}'
        '@keyframes spin{to{transform:rotate(360deg)}}'
        '.hot{animation:hot 2.4s ease-in-out infinite}'
        '@keyframes hot{0%,100%{fill:#2bb3c9}50%{fill:#7ee6f5}}'
        '.halo{transform-box:fill-box;transform-origin:center;animation:halo 3s ease-in-out infinite alternate}'
        '@keyframes halo{from{transform:scale(.9);opacity:.7}to{transform:scale(1.15);opacity:1}}'
        '.scope,.beacon{animation:blink 2.6s ease-in-out infinite}@keyframes blink{0%,100%{opacity:.9}50%{opacity:.25}}'
        '.coin{animation:coin 6s linear infinite}' +
        '@keyframes coin{0%%{transform:translate(0,0) scale(%s);opacity:0}10%%{opacity:1}85%%{opacity:1}'
        '100%%{transform:translate(%spx,%spx) scale(%s);opacity:0}}' % (f(csc), f(dx), f(dy), f(csc))
    )
    return defs, ''.join(out), style




# ---------------------------------------------------------------- card front

def svg_open(vx, vw, vh, iw, ih, aria, title, style, defs):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s 0 %s %s" width="%s" height="%s" role="img" '
            'aria-label="%s"><title>%s</title><style>%s</style><defs>%s</defs>'
            % (f(vx), f(vw), f(vh), f(iw), f(ih), aria, title, style, defs))


def half(v):
    """Rounds to the nearest 0.5 px, a whole device pixel on 2x screens."""
    return round(v * 2) / 2


def contrast(a, b):
    """WCAG contrast ratio of two hex colours."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
        return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def ink(font, s, size, tracking=0):
    """Outline points (x, y), y down, of s set from (0, 0) on the baseline; off-curve points
    included, so the points enclose the ink."""
    fnt = FONTS[font]
    items, _ = fnt.layout(s, tracking)
    sc = size / fnt.upm
    return [((gx + x) * sc, -y * sc) for g, gx in items for c in fnt.contours(g) for x, y, _ in c]


def title_block(doc, name, dia, top, hgt, cw, v, font):
    """Repo name vertically centred in the band, its leftmost ink TITLE_GAP right of the diamond's
    right tip. The tip is the diamond's rightmost point, so the name also clears its slanted edges.
    dia: diamond centre x, centre y and half diagonal, outline included.
    Returns (svg, ink right edge, size). The name's group carries class "nm"."""
    size = TITLE_SIZE[font][v]
    dcx, dcy, dr = dia
    y_mid = top + hgt / 2
    left = dcx + dr + TITLE_GAP[v]            # where the name's ink starts
    if font == 'pixel':
        y_top = half(y_mid - 3.5 * size)
        x = half(left)
        d, w = pixelfont.path(name, size, x, y_top)
        svg = '<path class="nm" d="%s" fill="%s" shape-rendering="crispEdges"/>' % (d, TITLE_FILL)
        right = x + w
    else:
        key = {'jost': 'tj', 'oxanium': 'to'}[font]
        base = y_mid + size * FONTS[key].cap / 2
        pts = ink(key, name, size, TITLE_TRACK[font])
        x = left - min(px for px, _ in pts)
        right = x + max(px for px, _ in pts)
        svg = doc.text(key, name, x, base, size, fill=TITLE_FILL, tracking=TITLE_TRACK[font], extra=' class="nm"')
    assert right <= cw - TITLE_MARGIN, (name, font, v, right, cw - TITLE_MARGIN)
    return svg, right, size


def effect_area(doc, v, T, p, L, cw):
    """The one line and its icons, laid out by the SETI rule: 1 icon left of the text,
    2 icons above it, 3 icons below it."""
    px0, py0, py1 = L['panel']
    lsize, pitch = L['line']
    lcap = FONTS['m'].cap * lsize
    pcx = (px0 + cw) / 2
    icons = p['icons']
    out, keep = [], []
    if len(icons) == 1:
        r = L['tok1']
        gap = 13 if v == 'wide' else 14
        maxw = cw - px0 - 2 * r - gap - 24
        lines = wrap('m', p['line'], lsize, maxw, 3)
        tw = max(width('m', ln, lsize) for ln in lines)
        gx = pcx - (2 * r + gap + tw) / 2
        tcx, tcy = gx + r, (py0 + py1) / 2
        block = lcap + pitch * (len(lines) - 1)
        top = tcy - block / 2
        tx = gx + 2 * r + gap
        out.append(token(tcx, tcy, r, T, icons[0], 'fx0'))
        out += [doc.text('m', ln, tx, top + lcap + pitch * i, lsize, fill=T['text']) for i, ln in enumerate(lines)]
        keep += [(tx - 3, top - 3, tx + tw + 3, top + block + 5), (tcx - r - 3, tcy - r - 3, tcx + r + 3, tcy + r + 3)]
    elif len(icons) == 3:
        ty_, tr, tgap = L['tok3']
        lines = wrap('m', p['line'], lsize, cw - px0 - 30, 2)
        block = lcap + pitch * (len(lines) - 1)
        top = py0 + (ty_ - tr - py0 - block) / 2
        out += [doc.text('m', ln, pcx, top + lcap + pitch * i, lsize, anchor='middle', fill=T['text'])
                for i, ln in enumerate(lines)]
        out += [token(pcx + (i - 1) * tgap, ty_, tr, T, ic, 'fx%d' % i) for i, ic in enumerate(icons)]
        tw_ = max(width('m', ln, lsize) for ln in lines) / 2 + 5
        keep += [(pcx - tw_, top - 3, pcx + tw_, top + block + 6), (pcx - tgap - tr - 3, ty_ - tr - 3, pcx + tgap + tr + 3, py1)]
    elif len(icons) == 2:
        _, tr, tgap = L['tok3']
        ty_ = py0 + tr + 7
        lines = wrap('m', p['line'], lsize, cw - px0 - 30, 2)
        block = lcap + pitch * (len(lines) - 1)
        top = ty_ + tr + (py1 - ty_ - tr - block) / 2
        out += [token(pcx + (i - .5) * tgap, ty_, tr, T, ic, 'fx%d' % i) for i, ic in enumerate(icons)]
        out += [doc.text('m', ln, pcx, top + lcap + pitch * i, lsize, anchor='middle', fill=T['text'])
                for i, ln in enumerate(lines)]
        tw_ = max(width('m', ln, lsize) for ln in lines) / 2 + 5
        keep += [(pcx - tw_, top - 3, pcx + tw_, top + block + 6), (pcx - tgap / 2 - tr - 3, py0, pcx + tgap / 2 + tr + 3, ty_ + tr + 3)]
    else:
        raise AssertionError('no effect layout for %d icons' % len(icons))
    return out, keep, lines


def title_band(doc, v, p, font):
    """Sector-colour band (class "band") with the repo name and the gold diamond at its left end.
    Returns (svg, title ink right edge, title size)."""
    L = LAYOUT[v]
    cw = L['cw']
    top, hgt = L['band']
    dcx, dr = L['diamond']
    dcy = top + hgt / 2
    col = p['sector']
    band = ('<rect class="band" x="-1" y="%s" width="%s" height="%s" fill="%s"/>' % (f(top), f(cw + 2), f(hgt), col) +
            '<rect x="-1" y="%s" width="%s" height="1" fill="#fff" opacity=".18"/>' % (f(top), f(cw + 2)) +
            '<rect x="-1" y="%s" width="%s" height="2" fill="%s"/>' % (f(top + hgt - 2), f(cw + 2), mix(col, '#000000', .3)))
    tsvg, tw, tsize = title_block(doc, p['name'], (dcx, dcy, dr + 1.5 * dr / 46), top, hgt, cw, v, font)
    return band + tsvg + diamond(dcx, dcy, dr, p['dia'](col)), tw, tsize


def card(v, T, p, aria, slot_pos):
    """slot_pos: 'left', 'mid' or 'right' for a wide card, None for a phone card."""
    L = LAYOUT[v]
    doc = Doc()
    cw, ch = L['cw'], L['ch']
    bar_y = L['band'][0]
    art_defs, art_svg, art_style = p['art'](v)
    pl_defs, pl_svg = planet(*L['planet'])
    defs = [FILTERS, art_defs, pl_defs]

    # top-left dark triangle with the radio dish; top-right sector triangle with the signal icon.
    # Both are 45 degree triangles with legs k.
    k = L['sector']
    dx, dy, ds = L['dish']
    sec_d = 'M%s -1H%sV%sZ' % (f(cw - k - 1), f(cw + 1), f(k + 1))
    ss, sc_ = signal_fit(p['signal'], k)
    corners = ('<path d="M-1 -1H%sL-1 %sZ" fill="%s"/>' % (f(k + 1), f(k + 1), CORNER) +
               '<g transform="%s">%s</g>' % (place(dx, dy, ds), icon_dish()) +
               '<path d="%s" fill="%s"/>' % (sec_d, p['sector']) +
               '<g transform="%s">%s</g>' % (place(cw - sc_, sc_, ss), signal_icon(p['signal'])))

    bar, _, _ = title_band(doc, v, p, TITLE_FONT)

    # effect panel with faint stars, the line and its icons
    px0, py0, py1 = L['panel']
    effect, keep, lines = effect_area(doc, v, T, p, L, cw)
    rnd = random.Random(41 if v == 'wide' else 43)
    dots = []
    while len(dots) < (16 if v == 'wide' else 12):
        x, y = rnd.uniform(px0 + 6, cw - 4), rnd.uniform(py0 + 4, py1 - 3)
        if any(a0 <= x <= a1 and b0 <= y <= b1 for a0, b0, a1, b1 in keep):
            continue
        dots.append('<circle cx="%.1f" cy="%.1f" r="%s" fill="#fff" opacity="%.2f"/>'
                    % (x, y, f(rnd.choice((.6, .8, 1.1, 1.5))), T['star'] * rnd.uniform(.5, 1)))
    pw, ph = cw - px0 + 10, py1 - py0 - 1
    panel = ('<rect x="%s" y="%s" width="%s" height="%s" rx="4" fill="%s" stroke="%s" stroke-width="1"/>'
             % (f(px0 + .5), f(py0 + .5), f(pw), f(ph), T['panel'], T['panel_line']) +
             '<g class="pst">%s</g>' % ''.join(dots))

    # flavour strip: rotated card code at the far left, italic flavour line
    cx_, cy0, cwid, chgt, csize = L['code']
    code = ('<rect x="%s" y="%s" width="%s" height="%s" rx="2" fill="%s"/>' % (f(cx_), f(cy0), f(cwid), f(chgt), T['code_bg']) +
            doc.text('c', p['code'], cx_ + cwid / 2 + csize * FONTS['c'].cap / 2, cy0 + chgt / 2, csize,
                     anchor='middle', fill=T['code'], rotate=-90, tracking=40))
    fl_x, fl_y, fl_size = L['flav']
    flav = doc.text('f', 'Claude Code plugin', fl_x, fl_y, fl_size, fill=T['flav'])

    # income corner (right-angled trapezoid, 45 degree left edge) and the strip along the bottom
    gh, gtop, gbot = L['income']
    st = L['strip']
    col = GOLD if p['income'] == 'credit' else GREEN
    inc_d = poly([(cw - gtop, ch - gh), (cw + 1, ch - gh), (cw + 1, ch + 1), (-1, ch + 1), (-1, ch - st), (cw - gbot + st, ch - st)])
    icx, icy = cw - gtop * .5, ch - gh * .5 - st * .2
    glyph = credit_glyph() if p['income'] == 'credit' else bolt()
    income = ('<path d="%s" fill="%s"/>' % (inc_d, col) +
              '<g transform="%s">%s</g>' % (place(icx, icy, gh * (.0098 if p['income'] == 'credit' else .0092)), glyph))

    body = [
        '<rect width="%s" height="%s" fill="%s"/>' % (f(cw), f(ch), T['body']),
        '<g clip-path="url(#ac)">%s%s</g>' % (art_svg, pl_svg),
        panel, ''.join(effect), code, flav, income, bar, corners,
    ]
    defs.append('<clipPath id="cc"><rect width="%s" height="%s" rx="%s"/></clipPath>' % (f(cw), f(ch), f(L['r'])) +
                '<clipPath id="ac"><rect width="%s" height="%s"/></clipPath>' % (f(cw), f(bar_y + .5)))
    defs.append(doc.defs())
    edge = ('<rect x=".5" y=".5" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="1"/>'
            % (f(cw - 1), f(ch - 1), f(L['r'] - .5), T['edge']))
    content = '<g clip-path="url(#cc)">%s</g>%s' % (''.join(body), edge)
    style = STYLE % (FRONT_STYLE + art_style)
    if slot_pos is None:      # phone: viewBox = card, intrinsic width PHONE_MAX
        head = svg_open(0, cw, ch + PHONE_GAP, PHONE_MAX, (ch + PHONE_GAP) * PHONE_MAX / cw, aria, p['name'],
                        style, ''.join(defs))
    else:                     # wide: viewBox = slot; the card sits at its slot offset
        off = {'left': 0, 'mid': (L['slot'] - cw) / 2, 'right': L['slot'] - cw}[slot_pos]
        head = svg_open(-off, L['slot'], ch, L['slot'], ch, aria, p['name'], style, ''.join(defs))
    return head + content + '</svg>\n', lines


def title_font_samples(out_dir):
    """Review only: both wide light cards with the repo name in each title-font candidate,
    written as title-<font>-<card>.svg."""
    global TITLE_FONT
    keep = TITLE_FONT
    out_dir.mkdir(parents=True, exist_ok=True)
    for font in TITLE_SIZE:
        TITLE_FONT = font
        for p in PROJECTS:
            svg, _ = card('wide', THEMES['light'], p, p['name'], 'left')
            (out_dir / ('title-%s-%s.svg' % (font, p['name']))).write_text(svg, encoding='utf-8')
    TITLE_FONT = keep


# ---------------------------------------------------------------- the two projects

PROJECTS = [
    dict(file='card-idevice-control', name='idevice-control', sector=BLUE, signal='signal-blue',
         code='MZ EN 01', art=art_idevice, icons=(tok_iphone, tok_ipad, tok_tv), slot='left',
         dia=dia_phone, income='energy', line='Lets Claude use a real iPhone, iPad or Apple TV.'),
    dict(file='card-cc-session-breakdown', name='cc-session-breakdown', sector=RED, signal='signal-red',
         code='MZ EN 02', art=art_ccsb, icons=(tok_pie,), slot='mid',
         dia=dia_pie, income='credit', line='Shows where your Claude Code usage went.'),
]

if __name__ == '__main__':
    check_symmetry()
    for p_ in PROJECTS:
        assert contrast(TITLE_FILL, p_['sector']) >= 4, (p_['name'], contrast(TITLE_FILL, p_['sector']))
    if sys.argv[1:2] == ['--title-fonts']:
        title_font_samples(pathlib.Path(sys.argv[2]))
        sys.exit()
    OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2] / 'assets'
    OUT.mkdir(parents=True, exist_ok=True)
    for theme, T in THEMES.items():
        for p in PROJECTS:
            aria = '%s: a Claude Code plugin. %s' % (p['name'], p['line'])
            for v in ('wide', 'phone'):
                svg, lines = card(v, T, p, aria, p['slot'] if v == 'wide' else None)
                out = OUT / ('%s%s-%s.svg' % (p['file'], '' if v == 'wide' else '-phone', theme))
                out.write_text(svg, encoding='utf-8')
                print(out.name, len(svg.encode()), lines)
    (OUT / 'blank.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"/>\n', encoding='utf-8')
    print('blank.svg')
