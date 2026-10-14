"""Build the footer: the Sun and the eight planets in a row under twinkling stars.

Usage: python3 build.py [out_dir]   (default: ../../../assets, the README assets folder)
Reads header.svg from the assets folder and writes footer.svg next to it. Run it after any
change to header.svg.

The footer reuses the header's drawing: the planet gradients, rock and comet symbols, clip paths,
the Sun block and the twinkle, Sun-glow and meteor CSS rules are copied out of header.svg by id or
by marker string. Changes made here:
- light comes from the left, where the Sun sits: radial gradient centres and the rim and
  atmosphere gradients turn toward the Sun, and each planet's drop shadow points away from it (+x);
- the planets stand in one row (ROW, x positions in px) on orbit rings centred on the Sun;
- new background stars, twinkling stars and sparkle crosses come from a seeded random generator, so
  the output is the same on every run;
- an asteroid belt between Mars and Jupiter, a comet past Neptune and two meteors.
Motion is CSS only; the prefers-reduced-motion rule stops all of it.
"""
import pathlib
import random
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2] / 'assets'
s = (OUT / 'header.svg').read_text(encoding='utf-8')


def elem(i):
    """The element with id i, copied whole from the header."""
    m = re.search(r'<(\w+)[^>]*\bid="' + i + r'"', s)
    tag = m.group(1)
    st = m.start()
    head = s[st:s.find('>', st) + 1]
    if head.endswith('/>'):
        return head
    return s[st:s.find('</' + tag + '>', st) + len(tag) + 3]


def group_around(idx):
    """Inner markup of the planet group (rotate + translate on the header's board) holding idx."""
    st = [m.start() for m in re.finditer(r'<g transform="rotate\([\d.]+\) translate\(0 -[\d.]+\)">', s[:idx])][-1]
    depth = 0
    for m in re.finditer(r'<g[\s>]|</g>', s[st:]):
        depth += -1 if m.group().startswith('</') else 1
        if depth == 0:
            en = st + m.end()
            break
    g = s[st:en]
    return g[g.find('>') + 1:-4]


def planet(key):
    body = group_around(s.find('url(#' + key + ')'))
    # drop shadow points away from the Sun (+x) instead of outward (-y)
    body = re.sub(r'<circle cy="-([\d.]+)" r="([\d.]+)" fill="url\(#pdr\)"/>',
                  lambda m: '<circle cx="%s" r="%s" fill="url(#pdr)"/>' % (m.group(1), round(float(m.group(2)), 2)), body)
    body = body.replace('<ellipse cy="-1.4" rx="17.6"', '<ellipse cx="1.4" rx="17.6"')
    return body


# defs: light comes from the left, where the Sun sits
defs = []
for g in ['gE', 'gMe', 'gV', 'gMa', 'gS', 'gU', 'gN']:
    defs.append(elem(g).replace('cx=".5" cy=".75"', 'cx=".25" cy=".5"'))
defs.append(elem('psh').replace('cx=".5" cy=".86"', 'cx=".14" cy=".5"'))
for g in ['rim', 'atm']:
    defs.append(elem(g).replace('x1="0" y1="0" x2="0" y2="1"', 'x1="1" y1="0" x2="0" y2="0"'))
for g in ['pdr', 'haze', 'mtl', 'gSun', 'gSl', 'sgl', 'sgd', 'gW', 'gSg', 'pmb', 'pmt', 'pmg', 'cSun',
          'cE', 'cV', 'cMa', 'cJ', 'cS', 'cU', 'ra', 'rb', 'rc', 'rd', 'cbl', 'chd', 'cmt']:
    defs.append(elem(g))

# the Sun block, from its glow circle to its outer ring
a = s.find('<circle r="34" fill="url(#gSg)" class="bsun"/>')
endtok = '<circle r="19.6" fill="none" stroke="#ff7420" stroke-width=".9" stroke-opacity=".4"/>'
sun = s[a:s.find(endtok, a) + len(endtok)]

# CSS: the header's rules for twinkles, Sun glow and meteors
css = []
want = ('.t1', '.t2', '.t3', '.t4', '.t5', '@keyframes tw', '.bsun', '.bsgr', '@keyframes bsgr',
        '@keyframes bsp', '.bsp1', '@keyframes bsgl', '.bm1', '@keyframes bm1', '.bm2', '@keyframes bm2')
for ln in s[s.find('<style>') + 7:s.find('</style>')].split('\n'):
    if ln.startswith(want):
        css.append(ln)
css.append('@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }')

W, H = 850, 100
CY = 50
SX = 60      # Sun x
SK = 1.5     # Sun scale
PK = 1.3     # planet scale
ROW = [('gMe', 132), ('gV', 188), ('gE', 248), ('gMa', 308), ('cJ', 466), ('gS', 566), ('gU', 664), ('gN', 750)]
rnd = random.Random(7)
o = []
o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
         'aria-label="McDyZzz footer: the Sun and the eight planets in a row"><title>McDyZzz footer</title>' % (W, H, W, H))
o.append('<style>' + '\n'.join(css) + '</style>')
o.append('<defs>' + ''.join(defs) + '<clipPath id="frame"><rect width="%d" height="%d" rx="18"/></clipPath></defs>' % (W, H))
o.append('<g clip-path="url(#frame)"><rect width="%d" height="%d" fill="#040508"/>' % (W, H))
# orbit rings around the Sun
o.append('<g fill="none" stroke="#fff" stroke-opacity=".13" stroke-width=".67">' +
         ''.join('<circle cx="%d" cy="%d" r="%d"/>' % (SX, CY, x - SX) for _, x in ROW) + '</g>')
# background stars, twinkling stars, sparkle crosses
st = []
for i in range(70):
    st.append('<circle cx="%.1f" cy="%.1f" r="%.2f" opacity="%.2f"/>' % (
        rnd.uniform(6, W - 6), rnd.uniform(5, H - 5), rnd.uniform(.3, .6), rnd.uniform(.3, .75)))
o.append('<g fill="#e4ecff">' + ''.join(st) + '</g>')
tw = []
for i in range(16):
    tw.append('<circle class="t%d" cx="%.1f" cy="%.1f" r="%.1f"/>' % (
        rnd.randint(1, 5), rnd.uniform(110, W - 10), rnd.uniform(6, H - 6), rnd.uniform(.5, .85)))
o.append('<g fill="#fff">' + ''.join(tw) + '</g>')
sp = ''.join('<path class="%s" d="M%g %gh4M%g %gv4"/>' % (c, x - 2, y, x, y - 2)
             for (x, y, c) in [(212, 16, 't2'), (398, 86, 't4'), (612, 14, 't1'), (708, 88, 't3'), (828, 22, 't5')])
o.append('<g stroke="#fff" stroke-width=".7" stroke-linecap="round">' + sp + '</g>')
# the Sun's warm wash
o.append('<g transform="translate(%g %g) scale(%g)"><circle r="170" fill="url(#gW)"/></g>' % (SX, CY, SK * 0.75))
# asteroid belt between Mars and Jupiter
belt = ['<ellipse cx="378" cy="%d" rx="38" ry="44" fill="url(#haze)"/>' % CY]
pts = [(352, 38), (360, 61), (368, 27), (372, 50), (381, 71), (385, 36), (390, 57), (398, 44), (404, 66), (357, 79),
       (395, 21), (376, 14), (408, 30), (349, 52), (364, 88), (386, 86)]
for (x, y) in pts:
    k = rnd.uniform(1.5, 3.2)
    f = rnd.choice([1, -1])
    belt.append('<use href="#%s" transform="translate(%g %g) scale(%.2f %.2f)"/>' % (rnd.choice(['ra', 'rb', 'rc', 'rd']), x, y, k * f, k))
o.append('<g>' + ''.join(belt) + '</g>')
# planets, comet, meteors, Sun
for key, x in ROW:
    o.append('<g transform="translate(%g %g) scale(%g)">%s</g>' % (x, CY, PK, planet(key)))
o.append('<use href="#cmt" transform="translate(806 34) rotate(98) scale(26)" opacity=".8"/>')
o.append('<g transform="translate(150 20) rotate(8)"><g class="bm1"><path d="M0 -.45L-20 0L0 .45A.45 .45 0 0 0 0 -.45Z" '
         'fill="url(#mtl)"/><circle r=".6" fill="#fff"/></g></g>')
o.append('<g transform="translate(560 84) rotate(-6)"><g class="bm2"><path d="M0 -.45L-24 0L0 .45A.45 .45 0 0 0 0 -.45Z" '
         'fill="url(#mtl)"/><circle r=".6" fill="#fff"/></g></g>')
o.append('<g transform="translate(%g %g) scale(%g)">%s</g>' % (SX, CY, SK, sun))
o.append('</g><rect x=".75" y=".75" width="%g" height="%g" rx="17.5" fill="none" stroke="#1d2a44" stroke-width="1.5"/></svg>'
         % (W - 1.5, H - 1.5))
txt = ''.join(o)
(OUT / 'footer.svg').write_text(txt, encoding='utf-8')
print('footer.svg', len(txt.encode()))
