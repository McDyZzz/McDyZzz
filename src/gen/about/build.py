"""Build the About images: the About list in about.md as glyph outlines, no box.

Usage: python3 build.py [out_dir]   (default: ../../../assets, the README assets folder)
Pure Python: text is laid out and outlined with ../tools/ttfpath.py (no system fonts, no compiler).

Font: BODY_FONT, the one body font of the page (Jost, SIL OFL 1.1, variable weight axis 100-900),
at WEIGHTS: 'r' for the text, 'b' for the bold BUT. To try another font, change BODY_FONT and
WEIGHTS and re-run.

Output, each in a light and a dark version:
- about-{light,dark}.svg: wide screens. 846 x H, two columns (items 1-3 left, 4-6 right).
  The README shows it without a width attribute, so at GitHub's 846 px README width it renders 1:1
  and the body text is `size` px. On a narrower README, max-width:100% scales it down.
- about-phone-{light,dark}.svg: narrow screens. 293 x H, one column. 293 px is the README width
  on a 375 px phone, where it renders 1:1.

The background is transparent, so GitHub's page colour shows through. The leftmost bullet tip sits
at x=0, so the list lines up with the left edge of header.svg.
Lines break greedily at spaces. A paragraph whose wrap leaves one word alone on a line gets a
narrower wrap width until no line holds a single word. The text itself stays exactly as in
about.md; BUT is drawn in capitals.
"""
import html
import pathlib
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools'))
from ttfpath import TTF  # noqa: E402

ABOUT = HERE / 'about.md'
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2] / 'assets'

# ---------------------------------------------------------------- type
BODY_FONT = HERE.parents[1] / 'fonts' / 'jost' / 'Jost[wght].ttf'
WEIGHTS = {'r': 430, 'b': 680}
FONTS = {k: TTF(str(BODY_FONT), wght=w) for k, w in WEIGHTS.items()}
TRACK = {'r': 0, 'b': 0.04}         # extra letter spacing per font, in em
SPACE = 0.84                        # word space as a share of the font's own (Jost's 0.3 em reads loose)
SHRINK = 6                          # wrap width step when a line holds a single word

# Layout per variant, in px at the README width the variant is made for.
# cols: item indexes per column. gutter: space between columns. tx: text start right of the bullet.
VARIANTS = {
    'about': dict(W=846, size=15, lh=23, pgap=7.5, d=3.3, stroke=1.3, tx=19, cols=[[0, 1, 2], [3, 4, 5]], gutter=42),
    'about-phone': dict(W=293, size=14, lh=21, pgap=7, d=3.1, stroke=1.2, tx=16, cols=[[0, 1, 2, 3, 4, 5]], gutter=0),
}

# Colours per GitHub theme. BUT on light (#9a6700 on #ffffff) is 4.9:1.
THEMES = {
    'light': {'text': '#1f2328', 'but': '#9a6700', 'bullet': '#0969da', 'hole': '#ffffff', 'rail': '#b6cbe8'},
    'dark':  {'text': '#e6edf3', 'but': '#f2b84b', 'bullet': '#6cb6ff', 'hole': '#0d1117', 'rail': '#2b3d5e'},
}

# ---------------------------------------------------------------- About text, exactly as in about.md
items = [ln[2:] for ln in ABOUT.read_text(encoding='utf-8').splitlines() if ln.startswith('- ')]
assert len(items) == 6, items
paras = []
for it in items:
    chars = []
    for i, part in enumerate(re.split(r'\*\*(.+?)\*\*', it)):
        chars += [(ch, 'b' if i % 2 else 'r') for ch in (part.upper() if i % 2 else part)]
    paras.append(chars)
ALT = 'About: ' + ' '.join('- ' + it.replace('**', '') for it in items)


def f1(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def place_run(chars, size):
    """Glyph positions for a run of (char, font) pairs: [(font, gid, x)], total width in px.
    Kerning applies between neighbours in the same font."""
    out, x, prev = [], 0.0, None
    for ch, fk in chars:
        fnt = FONTS[fk]
        sc = size / fnt.upm
        g = fnt.gid(ch)
        if prev and prev[0] == fk:
            x += fnt.kern_pair(prev[1], g) * sc
        out.append((fk, g, x))
        x += fnt.adv[g] * sc * (SPACE if ch == ' ' else 1) + TRACK[fk] * size
        prev = (fk, g)
    return out, x


def wrap(chars, size, width):
    """Greedy line break at spaces. Returns lines as lists of (char, font)."""
    words, cur = [], []
    for c in chars:
        if c[0] == ' ':
            words.append(cur)
            cur = []
        else:
            cur.append(c)
    words.append(cur)
    space = [(' ', 'r')]
    lines, line = [], []
    for w in words:
        trial = line + space + w if line else w
        if line and place_run(trial, size)[1] > width:
            lines.append(line)
            line = w
        else:
            line = trial
    lines.append(line)
    return lines


def build(name, v):
    ncol = len(v['cols'])
    colw = (v['W'] - v['gutter'] * (ncol - 1)) / ncol
    size = v['size']
    # wrap: shrink a paragraph's width while any of its lines holds a single word
    laid = []
    for chars in paras:
        width = colw - v['tx']
        for _ in range(80):
            lines = wrap(chars, size, width)
            if all(' ' in ''.join(c for c, _ in ln) for ln in lines):
                break
            width -= SHRINK
        else:
            sys.exit('could not avoid single-word lines')
        laid.append(lines)

    fr = FONTS['r']
    cap, xh, desc = fr.cap * size, fr.s16(fr.t['OS/2'] + 86) / fr.upm * size, 0.25 * size
    ids, defs = {}, []

    def gid(fk, g):
        k = (fk, g)
        if k not in ids:
            d = FONTS[fk].glyph_d(g)
            if not d:
                return None
            ids[k] = '%s%x' % (fk, g)
            defs.append('<path id="%s" d="%s"/>' % (ids[k], d))
        return ids[k]

    lh, pgap, d, sw = v['lh'], v['pgap'], v['d'], v['stroke']
    sc = size / fr.upm
    pt = 3                                   # top margin above the first cap line
    marks, rows, rails, bottom = [], [], [], 0
    for ci, col in enumerate(v['cols']):
        x0 = ci * (colw + v['gutter'])
        bx = x0 + d + sw / 2                 # bullet centre: the left tip touches the column edge
        y = pt + cap
        first = []
        for k, p in enumerate(col):
            if k:
                y += lh + pgap
            first.append(y - xh / 2)
            for j, ln in enumerate(laid[p]):
                if j:
                    y += lh
                reg, bold = [], []
                for fk, g, gx in place_run(ln, size)[0]:
                    i = gid(fk, g)
                    if i:
                        u = '<use href="#%s" x="%s"/>' % (i, f1(gx / sc))
                        (bold if fk == 'b' else reg).append(u)
                row = '<g transform="translate(%s %s) scale(%.5f)">%s' % (f1(x0 + v['tx']), f1(y), sc, ''.join(reg))
                if bold:
                    row += '<g class="but">%s</g>' % ''.join(bold)
                rows.append(row + '</g>')
        bottom = max(bottom, y + desc)
        marks += ['<use href="#dm" x="%s" y="%s"/>' % (f1(bx), f1(b)) for b in first]
        rails.append('M%s %sV%s' % (f1(bx), f1(first[0]), f1(first[-1])))
    H = round(bottom + 3)
    W = v['W']
    diamond = 'M0 %sL%s 0L0 %sL%s 0Z' % (f1(-d), f1(d), f1(d), f1(-d))
    dash = '%s %s %s %s' % (f1(size * .12), f1(size * .2), f1(size * .4), f1(size * .2))
    OUT.mkdir(parents=True, exist_ok=True)
    for theme, c in THEMES.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
               'aria-label="{alt}"><title>About</title><defs>{defs}<path id="dm" d="{dm}"/></defs>'
               '<path d="{rail}" stroke="{RC}" stroke-width="1.2" stroke-dasharray="{dash}" fill="none"/>'
               '<g fill="{HC}" stroke="{BC}" stroke-width="{SW}" stroke-linejoin="round">{marks}</g>'
               '<g fill="{TEXT}">{rows}</g>'
               '</svg>\n').format(W=W, H=H, alt=html.escape(ALT, quote=True), defs=''.join(defs), dm=diamond,
                                  rail=''.join(rails), RC=c['rail'], dash=dash, HC=c['hole'], BC=c['bullet'], SW=sw,
                                  marks=''.join(marks), TEXT=c['text'],
                                  rows=''.join(rows).replace('class="but"', 'fill="%s"' % c['but']))
        out = OUT / ('%s-%s.svg' % (name, theme))
        out.write_text(svg, encoding='utf-8')
        print(out.name, '%dx%d' % (W, H), 'text %gpx' % size, 'lines', sum(map(len, laid)), 'bytes', len(svg.encode()))
    for p, lines in enumerate(laid):
        for ln in lines:
            print('  %d| %s' % (p, ''.join(c for c, _ in ln)))


for name, v in VARIANTS.items():
    build(name, v)
