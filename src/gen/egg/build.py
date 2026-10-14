"""Build the "Don't click this." easter egg images: the line in the <summary> and the three lines it
reveals, as glyph outlines in the About font.

Usage: python3 build.py [out_dir]   (default: ../../../assets, the README assets folder)
Pure Python: text is laid out and outlined with ../tools/ttfpath.py.

Font and colours match the About images (../about/build.py): Jost (SIL OFL 1.1) at weight 430, the
same word spacing, the About text colour per GitHub theme, transparent background.

Output, each in a light and a dark version (-light.svg, -dark.svg):
- egg-summary, egg-summary-phone: "Don't click this." at the About body size (15 px wide, 14 px phone).
  GitHub draws an inline image with its bottom edge on the text baseline, and the disclosure
  triangle sits on that same baseline. So the image's bottom edge is the text baseline plus PAD for
  the overshoot of round letters; the text then lines up with the triangle.
- egg-reveal, egg-reveal-phone: the three revealed lines at the About body size and line pitch.
The text starts at the pen position x=0, as browser text would. Each image is its own size: the
README shows it without a width attribute, so it renders 1:1.
"""
import html
import math
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools'))
from ttfpath import TTF  # noqa: E402

BODY_FONT = HERE.parents[1] / 'fonts' / 'jost' / 'Jost[wght].ttf'
FONT = TTF(str(BODY_FONT), wght=430)
SPACE = 0.84          # word space as a share of the font's own, as in About
PAD = 1               # px of room around the ink; below the summary baseline it covers the overshoot

SUMMARY = "Don't click this."
REVEAL = ['I taught Claude to tap my iPhone.', 'Then it wanted the Apple TV remote.', 'Now it reads my token bills.']
# size: font size in px, lh: line pitch in px (About: wide 15 / 23, phone 14 / 21)
VARIANTS = {'': dict(size=15, lh=23), '-phone': dict(size=14, lh=21)}
THEMES = {'light': '#1f2328', 'dark': '#e6edf3'}


def f(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def layout(s):
    """[(gid, x)] in font units with kerning and the narrowed word space."""
    out, x, prev = [], 0.0, None
    for ch in s:
        g = FONT.gid(ch)
        if prev is not None:
            x += FONT.kern_pair(prev, g)
        out.append((g, x))
        x += FONT.adv[g] * (SPACE if ch == ' ' else 1)
        prev = g
    return out


def ink_box(items):
    """Ink bounds (x0, y0, x1, y1) in font units, y down, of a laid-out line on baseline 0."""
    pts = [(gx + x, -y) for g, gx in items for c in FONT.contours(g) for x, y, _ in c]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def image(lines, size, lh, colour, alt, title, baseline_bottom):
    """SVG of `lines` at `size` px, `lh` px apart. baseline_bottom: the last baseline sits PAD above
    the bottom edge (for an image that sits on the text baseline); else the bottom edge clears the
    descenders by PAD."""
    sc = size / FONT.upm
    laid = [layout(ln) for ln in lines]
    boxes = [ink_box(it) for it in laid]
    assert all(b[0] >= 0 for b in boxes), 'ink left of x=0'
    w = math.ceil(max(b[2] for b in boxes) * sc + PAD)
    span = -boxes[0][1] * sc + lh * (len(lines) - 1)               # first ink top to the last baseline
    if baseline_bottom:
        assert boxes[-1][3] * sc <= PAD, 'ink more than PAD below the baseline'
        h = math.ceil((span + 2 * PAD) * 2) / 2                    # whole device px on 2x screens
        last = h - PAD
    else:
        h = math.ceil((span + boxes[-1][3] * sc + 2 * PAD) * 2) / 2
        last = PAD + span
    bases = [last - lh * (len(lines) - 1 - i) for i in range(len(lines))]
    ids, defs, rows = {}, [], []
    for it, base in zip(laid, bases):
        uses = []
        for g, gx in it:
            if g not in ids:
                d = FONT.glyph_d(g)
                ids[g] = 'j%x' % g if d else None
                if d:
                    defs.append('<path id="j%x" d="%s"/>' % (g, d))
            if ids[g]:
                uses.append('<use href="#%s" x="%s"/>' % (ids[g], f(gx)))
        rows.append('<g transform="translate(0 %s) scale(%.5f)">%s</g>' % (f(base), sc, ''.join(uses)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%s" height="%s" role="img" '
            'aria-label="%s"><title>%s</title><defs>%s</defs><g class="tx" fill="%s">%s</g></svg>\n'
            % (w, f(h), w, f(h), html.escape(alt, quote=True), html.escape(title), ''.join(defs), colour,
               ''.join(rows))), w, h


if __name__ == '__main__':
    OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2] / 'assets'
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix, v in VARIANTS.items():
        for theme, colour in THEMES.items():
            for name, lines, on_base in (('egg-summary', [SUMMARY], True), ('egg-reveal', REVEAL, False)):
                svg, w, h = image(lines, v['size'], v['lh'], colour, ' '.join(lines), ' '.join(lines), on_base)
                out = OUT / ('%s%s-%s.svg' % (name, suffix, theme))
                out.write_text(svg, encoding='utf-8')
                print(out.name, '%sx%s' % (w, f(h)), 'text %gpx' % v['size'], 'bytes', len(svg.encode()))
