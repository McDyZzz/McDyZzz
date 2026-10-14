"""Build the section heading tags "ABOUT" and "FEATURED PROJECTS" in a light and a dark version,
each for wide screens and for phones.

Usage: python3 headings.py [out_dir]   (default: ../../assets, the README assets folder)
Output: h-about-{light,dark}.svg, h-about-phone-{light,dark}.svg, and the same for h-project.
The README shows each tag in a plain paragraph without a width or height attribute, so it renders
at the SVG's own size: SIZES['wide'] at the 846 px README width, SIZES['phone'] at 293 px.
Each tag: slanted box, glowing chip icon with signal bars, the label in capitals.
The chip's left edge sits at x=0, in line with the header and the About bullets.

Label font: Oxanium (SIL OFL 1.1, variable weight 200-800), the repo-name font of the cards, at
WEIGHT, as glyph outlines via tools/ttfpath.py. `cap` is the cap height in CSS px: wide 10.5 px
(21 device px on 2x screens), phone 28/3 px (28 device px on 3x screens); the font size follows
from the font's cap height. The baseline sits on the device pixel grid, so the flat tops and
bottoms of the capitals stay crisp. TRACK spaces the capitals apart.
"""
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'tools'))
from ttfpath import TTF  # noqa: E402

OXANIUM = HERE.parent / 'fonts' / 'oxanium' / 'Oxanium[wght].ttf'
WEIGHT = 600
TRACK = 110          # letter spacing in font units (1000 per em)
FONT = TTF(str(OXANIUM), wght=WEIGHT)

THEMES = {
    'light': {'fill': '#f6f8fa', 'border': '#d1d9e0', 'text': '#1f2328'},
    'dark':  {'fill': '#161b22', 'border': '#30363d', 'text': '#e6edf3'},
}
# h: SVG height in px. cap: label cap height in px. grid: device pixel in CSS px (2x wide, 3x phone).
SIZES = {'wide': {'h': 30, 'cap': 10.5, 'grid': .5}, 'phone': {'h': 26, 'cap': 28 / 3, 'grid': 1 / 3}}
LABELS = {'h-about': ('ABOUT', 'About'), 'h-project': ('FEATURED PROJECTS', 'Featured projects')}

# Chip icon with signal bars, drawn on a 36 px tall tag and scaled with the tag.
CHIP = 'M-15 -9.5Q-15 -12.5 -12 -12.5L4 -12.5Q7 -12.5 8.9 -10.2L15.1 -2.3Q17 0 15.1 2.3L8.9 10.2Q7 12.5 4 12.5L-12 12.5Q-15 12.5 -15 9.5Z'
BARS = 'M-5.1 -2.5V2.5M-1.7 -4.5V4.5M1.7 -6.5V6.5M5.1 -3.5V3.5'
STYLE = ('.p{animation:p 2.6s ease-in-out infinite alternate}'
         '@keyframes p{from{opacity:.3}to{opacity:.85}}'
         '@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }')


def f(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def label_ink(label):
    """Glyph placements [(gid, x)] in font units and the ink's left and right edge in font units."""
    items, _ = FONT.layout(label, TRACK)
    xs = [gx + x for g, gx in items for c in FONT.contours(g) for x, _, _ in c]
    return items, min(xs), max(xs)


def heading(label, title, h, cap, grid, c):
    s = h / 36                                   # scale against the 36 px original tag
    cy = h / 2
    ox = 11.3 * s                                # shift left so the chip icon's left edge sits at x=0
    sc = cap / FONT.cap / FONT.upm               # font units to px
    items, ink_l, ink_r = label_ink(label)
    tx = 56 * s - ox                             # left edge of the label's ink
    base = round((cy + cap / 2) / grid) * grid   # baseline on the device pixel grid
    text_w = (ink_r - ink_l) * sc
    box_x, box_h = 30 * s - ox, 24 * s
    box_w = tx - box_x + text_w + 12 * s
    w = box_x + box_w + box_h / 2 * 0.25 + 1     # skewX(-14) leans the top edge right by h/2*tan(14)
    used = sorted({g for g, _ in items if FONT.glyph_d(g)})
    defs = ''.join('<path id="o%x" d="%s"/>' % (g, FONT.glyph_d(g)) for g in used)
    uses = ''.join('<use href="#o%x" x="%d"/>' % (g, gx) for g, gx in items if g in used)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        'aria-label="{title}"><title>{title}</title><style>{style}</style><defs>'
        '<filter id="g" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="{blur}"/></filter>'
        '{defs}</defs>'
        '<g transform="translate({bx} {cy}) skewX(-14)"><rect class="box" x="0" y="{by}" width="{bw}" height="{bh}" '
        'fill="{fill}" stroke="{border}" stroke-width="1"/></g>'
        '<circle class="p" cx="{ix}" cy="{cy}" r="{gr}" fill="#0184d5" filter="url(#g)"/>'
        '<g transform="translate({ix} {cy}) scale({isc})">'
        '<path d="{chip}" fill="#4a68b0" stroke="#0b1530" stroke-width="2.6" stroke-linejoin="round"/>'
        '<path d="{chip}" fill="none" stroke="#fff" stroke-width=".8" opacity=".35" transform="scale(.84)"/>'
        '<path d="{bars}" fill="none" stroke="#0b1530" stroke-width="4.6" stroke-linecap="round"/>'
        '<path d="{bars}" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></g>'
        '<g class="lb" transform="translate({tx} {base}) scale({sc})" fill="{text}">{uses}</g>'
        '</svg>\n'
    ).format(w=f(w), h=f(h), title=title, style=STYLE, blur=f(3 * s), defs=defs, bx=f(box_x), cy=f(cy),
             by=f(-box_h / 2), bw=f(box_w), bh=f(box_h), fill=c['fill'], border=c['border'], ix=f(26 * s - ox),
             gr=f(13 * s), isc=f(0.9 * s), chip=CHIP, bars=BARS, tx=f(tx - ink_l * sc), base=f(base),
             sc='%.6f' % sc, text=c['text'], uses=uses)


if __name__ == '__main__':
    OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / 'assets'
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (label, title) in LABELS.items():
        for size, z in SIZES.items():
            for theme, c in THEMES.items():
                svg = heading(label, title, z['h'], z['cap'], z['grid'], c)
                out = OUT / ('%s%s-%s.svg' % (name, '' if size == 'wide' else '-phone', theme))
                out.write_text(svg, encoding='utf-8')
                print(out.name, len(svg.encode()), 'Oxanium %d at %.2f px' % (WEIGHT, z['cap'] / FONT.cap))
