"""Extracts SETI icons from the fan-site sprite sheet and traces them to vector outlines.

Run: python3 extract_icons.py [sheet.webp]   (needs Pillow with WebP support)

Source: seti-icons.webp, the v1 sheet of seti.ender-wiggin.com (5 columns x 7 rows of 296 px
cells). The owner approved using these icons on the profile cards. The sheet stays out of the
repo: its path is the first argument, else the SETI_ICON_SHEET environment variable, else
../../local/ender-wiggin/seti-icons.webp (src/local/ is gitignored).
A normal rebuild does not run this script: the cards read the committed seti_icons.json.

Each cell is a coloured square with the icon on it. For every icon used on the cards:
1. matte: each pixel's share of the icon colour against the cell background (the median colour of
   a ring just inside the cell edge; the outer 6 px of the cell are ignored, they bleed from the
   neighbour cells);
2. trace: marching squares at matte 0.5 with sub-pixel edge positions, then each closed outline is
   simplified (Ramer-Douglas-Peucker, TOLERANCE px). Specks under MIN_AREA px are dropped.
Output:
- seti_icons.json: per icon, per colour layer, a list of outlines. Each outline holds its SVG path
  data and bounding box on a 100-unit grid: the cell spans -50..50 on both axes, centre (0, 0),
  y down. Draw a layer with fill-rule evenodd (holes are separate outlines).
- ../../local/icons-png/<icon>.png: the matte as a clean transparent image (icon colour on
  transparent), for review. These stay out of the repo, like the sheet.
Icons and layers:
- credit (cell 0,0), energy (1,0), signal-red (2,2), signal-blue (3,2): one white layer 'glyph'.
  The signal bars are separate outlines, so a card can animate each bar.
- move (1,1): 'arrow' = the whole lavender-and-white silhouette, 'probe' = the white parts only
  (satellite and debris dots), drawn on top of the arrow layer.
"""
import json
import math
import os
import pathlib
import statistics
import sys

from PIL import Image

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
LOCAL = HERE.parents[1] / 'local'
SHEET = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                     os.environ.get('SETI_ICON_SHEET', LOCAL / 'ender-wiggin' / 'seti-icons.webp'))
PNG_DIR = LOCAL / 'icons-png'
CELL = 296
EDGE = 6            # px at each cell edge treated as background
TOLERANCE = 0.55    # px, outline simplification
MIN_AREA = 14       # px^2, smaller outlines are noise

ICONS = {
    'credit': (0, 0),
    'energy': (1, 0),
    'move': (1, 1),
    'signal-red': (2, 2),
    'signal-blue': (3, 2),
}


def cell_pixels(sheet, col, row):
    img = sheet.crop((col * CELL, row * CELL, col * CELL + CELL, row * CELL + CELL)).convert('RGB')
    return [[img.getpixel((x, y)) for x in range(CELL)] for y in range(CELL)]


def background(px):
    ring = [px[y][x] for y in range(EDGE, CELL - EDGE) for x in range(EDGE, CELL - EDGE)
            if min(x, y, CELL - 1 - x, CELL - 1 - y) < EDGE + 10]
    return tuple(statistics.median(p[c] for p in ring) for c in range(3))


def matte_toward(px, bg, fg):
    """Share of colour fg in each pixel against bg: projection of (p - bg) onto (fg - bg)."""
    d = [fg[c] - bg[c] for c in range(3)]
    n = sum(v * v for v in d)
    out = []
    for y in range(CELL):
        row = []
        for x in range(CELL):
            if min(x, y, CELL - 1 - x, CELL - 1 - y) < EDGE:
                row.append(0.0)
                continue
            p = px[y][x]
            a = sum((p[c] - bg[c]) * d[c] for c in range(3)) / n
            row.append(min(1.0, max(0.0, a)))
        out.append(row)
    return out


def matte_white_only(px, low):
    """White parts of a white-and-lavender icon: min channel from `low` (lavender) up to 255."""
    out = []
    for y in range(CELL):
        row = []
        for x in range(CELL):
            if min(x, y, CELL - 1 - x, CELL - 1 - y) < EDGE:
                row.append(0.0)
                continue
            m = min(px[y][x])
            row.append(min(1.0, max(0.0, (m - low) / (255 - low))))
        out.append(row)
    return out


# ---------------------------------------------------------------- tracing

def trace(a, level=0.5):
    """Closed outlines of the region a >= level, as lists of (x, y) in pixel-centre coordinates."""
    h, w = len(a), len(a[0])

    def v(x, y):
        return a[y][x] if 0 <= x < w and 0 <= y < h else 0.0

    def point(e):
        kind, x, y = e
        if kind == 'h':                 # edge (x, y)-(x+1, y)
            v0, v1 = v(x, y), v(x + 1, y)
            return (x + (level - v0) / (v1 - v0), y)
        v0, v1 = v(x, y), v(x, y + 1)   # edge (x, y)-(x, y+1)
        return (x, y + (level - v0) / (v1 - v0))

    nxt = {}
    for y in range(-1, h):
        for x in range(-1, w):
            tl, tr, br, bl = v(x, y) >= level, v(x + 1, y) >= level, v(x + 1, y + 1) >= level, v(x, y + 1) >= level
            code = tl * 8 + tr * 4 + br * 2 + bl
            if code in (0, 15):
                continue
            top, right, bottom, left = ('h', x, y), ('v', x + 1, y), ('h', x, y + 1), ('v', x, y)
            # segments oriented with the inside on the right
            table = {
                1: [(bottom, left)], 2: [(right, bottom)], 3: [(right, left)], 4: [(top, right)],
                6: [(top, bottom)], 7: [(top, left)], 8: [(left, top)], 9: [(bottom, top)],
                11: [(right, top)], 12: [(left, right)], 13: [(bottom, right)], 14: [(left, bottom)],
            }
            if code in (5, 10):
                centre = (v(x, y) + v(x + 1, y) + v(x + 1, y + 1) + v(x, y + 1)) / 4 >= level
                if code == 5:
                    segs = [(top, right), (bottom, left)] if not centre else [(top, left), (bottom, right)]
                else:
                    segs = [(left, top), (right, bottom)] if not centre else [(left, bottom), (right, top)]
            else:
                segs = table[code]
            for s, e in segs:
                nxt[s] = e
    loops = []
    while nxt:
        start, e = nxt.popitem()
        loop = [point(start)]
        while e != start:
            loop.append(point(e))
            e = nxt.pop(e)
        loops.append(loop)
    return loops


def area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1e-9
    best, idx = -1, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x1 * y0 - y1 * x0) / n
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return rdp(pts[:idx + 1], tol)[:-1] + rdp(pts[idx:], tol)


def simplify_closed(loop, tol):
    far = max(range(len(loop)), key=lambda i: math.dist(loop[0], loop[i]))
    a = rdp(loop[:far + 1], tol)
    b = rdp(loop[far:] + [loop[0]], tol)
    return a[:-1] + b[:-1]


def to_grid(p):
    """Pixel-centre coordinates -> 100-unit grid centred on the cell."""
    return ((p[0] + .5 - CELL / 2) * 100 / CELL, (p[1] + .5 - CELL / 2) * 100 / CELL)


def fmt(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def outlines(a):
    out = []
    for loop in trace(a):
        if area(loop) < MIN_AREA:
            continue
        pts = [to_grid(p) for p in simplify_closed(loop, TOLERANCE)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append({'d': 'M' + 'L'.join('%s %s' % (fmt(x), fmt(y)) for x, y in pts) + 'Z',
                    'bbox': [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]})
    out.sort(key=lambda o: (o['bbox'][0], o['bbox'][1]))
    return out


def save_png(a, colour, path):
    img = Image.new('RGBA', (CELL, CELL))
    img.putdata([colour + (round(255 * v),) for row in a for v in row])
    img.save(path)


def main():
    if not SHEET.is_file():
        sys.exit('sprite sheet not found: %s (pass its path or set SETI_ICON_SHEET)' % SHEET)
    sheet = Image.open(SHEET)
    assert sheet.size == (5 * CELL, 7 * CELL), sheet.size
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    result = {'source': 'seti-icons.webp, the v1 sheet of seti.ender-wiggin.com', 'grid': 'cell = -50..50, centre 0 0, y down',
              'icons': {}}
    for name, (col, row) in ICONS.items():
        px = cell_pixels(sheet, col, row)
        bg = background(px)
        if name == 'move':
            # lavender: the commonest bluish light colour in the cell
            lav_px = [p for r in px for p in r if p[2] - p[0] > 14 and min(p) > 170]
            lav = tuple(statistics.median(p[c] for p in lav_px) for c in range(3))
            silhouette = matte_toward(px, bg, lav)
            white = matte_white_only(px, min(lav) + 6)
            layers = {'arrow': outlines(silhouette), 'probe': outlines(white)}
            save_png(silhouette, tuple(round(c) for c in lav), PNG_DIR / 'move-arrow.png')
            save_png(white, (255, 255, 255), PNG_DIR / 'move-probe.png')
            colours = {'arrow': '#%02x%02x%02x' % tuple(round(c) for c in lav), 'probe': '#ffffff'}
        else:
            a = matte_toward(px, bg, (255, 255, 255))
            layers = {'glyph': outlines(a)}
            save_png(a, (255, 255, 255), PNG_DIR / (name + '.png'))
            colours = {'glyph': '#ffffff'}
        result['icons'][name] = {'cell': [col, row], 'background': '#%02x%02x%02x' % tuple(round(c) for c in bg),
                                 'colours': colours, 'layers': layers}
        print(name, 'bg', result['icons'][name]['background'],
              {k: (len(v), sum(len(o['d']) for o in v)) for k, v in layers.items()})
    (HERE / 'seti_icons.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
