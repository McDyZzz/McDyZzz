"""Builds the card back: the draw pile in the third slot of the desktop card row.

Run: python3 build_back.py [out_dir]   (default: ../../../assets, the README assets folder)
Needs ../cards/build_cards.py (slot and card geometry, themes, number format, colour mix).

Output: card-back-light.svg and card-back-dark.svg, for GitHub's light and dark pages. They differ
only in the strength of the pile's contact shadow (SHADOW).

The pile fills a LAYOUT['wide'] slot like the card fronts: the 262 x 403 card box on the right of
the 281 px slot, the transparent rest on the left is the gutter.

Top card (poster_art): a 1950s travel poster. Only the 12 colours of the retro travel-poster style
(POSTER) and mixes of them; every face is two flat tones; no outlines; no gradients inside the
illustration. One paper layer on top: fine grain, low-frequency mottling and a vignette (the
vignette is the only gradient). An off-white paper margin (FRAME) surrounds the scene; it carries
the fine grain, faint pale fibres and a light vignette, all neutral so the margin stays clean next
to GitHub's white page. The top face stays flat; the depth is only in the pile.

Pile (pile): a block of off-white card stock seen from above and slightly in front, lit from the upper
right like the poster scene. The top card's top and right edges sit on the card box's top and right
edges. PILE['cards'] cards lie under it, each a step further left and down, PILE['depth'] in all,
so the block shows a front face along the bottom and a side face on the left, both in shade.
- Each card is a rounded rectangle with a hairline edge, so the faces carry fine layer lines; the
  steps vary a little, and a stronger gap line marks every few cards.
- The cards darken toward the table; the left face is darker than the front face, the front face
  brightens where it turns toward the light at the bottom right.
- The middle of the stack bulges PILE['bulge'] to the left, and the PILE['loose'] cards sit a
  little off line (small shifts and turns).
- The top card has a pale rim on its face and a pale edge over a dark gap.
- A soft contact shadow falls down and to the left, into the gutter; a mask fades it out before
  the bottom edge of the image (PILE['foot'] px under the pile).
Motion is CSS only; the prefers-reduced-motion rule (REDUCE) stops all of it, and the still frame
is the full design (rocket trail drawn).
"""
import math
import pathlib
import random
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'cards'))
from build_cards import LAYOUT, THEMES, f, mix, poly, svg_open  # noqa: E402

REDUCE = '@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }'
TWINKLE = ('.t1{animation:tw 3.2s ease-in-out infinite alternate}'
           '.t2{animation:tw 4.4s ease-in-out -1.6s infinite alternate}'
           '.t3{animation:tw 5.6s ease-in-out -3.1s infinite alternate}'
           '@keyframes tw{from{opacity:1}to{opacity:.2}}')


# ---------------------------------------------------------------- shared helpers

def v_add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def v_mul(v, k):
    return tuple(c * k for c in v)


def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


def hull(pts):
    """Convex hull (monotone chain)."""
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(reversed(pts))
    return lo[:-1] + up[:-1]


def star4(x, y, s, k=.22):
    """Four-point star with concave sides, centre (x, y), tip radius s; k = waist radius / s."""
    w = s * k
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        r = s if i % 2 == 0 else w
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    return poly(pts)


def arc_pts(cx, cy, r, a0, a1, n=48, ry=None):
    """Points on a circle (or ellipse with ry) from angle a0 to a1 (radians, screen y down)."""
    ry = r if ry is None else ry
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def crescent(cx, cy, r, ox, oy, r2, n=40):
    """The part of circle (cx, cy, r) outside circle (cx + ox, cy + oy, r2), as a polygon."""
    d = math.hypot(ox, oy)
    phi = math.atan2(oy, ox)
    al = math.acos((d * d + r * r - r2 * r2) / (2 * d * r))
    outer = arc_pts(cx, cy, r, phi + al, phi + 2 * math.pi - al, n)
    ix, iy = cx + ox, cy + oy
    (px, py), (qx, qy) = outer[0], outer[-1]
    tq, tp = math.atan2(qy - iy, qx - ix), math.atan2(py - iy, px - ix)
    for k in (0, 1, -1):
        pts = arc_pts(ix, iy, r2, tq, tp + 2 * math.pi * k, n)
        mx, my = pts[n // 2]
        if math.hypot(mx - cx, my - cy) < r and abs(tp + 2 * math.pi * k - tq) < 2 * math.pi:
            return outer + pts[1:-1]
    raise ValueError('no crescent')


# ---------------------------------------------------------------- the top card: a travel poster

# The 12 colours of the retro travel-poster style. Other tones are mixes of these.
POSTER = dict(cream='#F3DDB3', sunset='#E4572E', ochre='#D9763A', deepTeal='#1D4E63', reefTeal='#1E7C86',
              turquoise='#3AB5AD', skyBlue='#6C9DC6', skyBlueLight='#BAD1E0', ink='#2E3A40', sand='#C9B48A',
              gumGreen='#3F6E4A', wattle='#E3AE45')
C = POSTER
FRAME = '#f4f2ee'                                    # off-white paper margin round the scene


def flat_cloud(uid, x0, x1, base, hgt, lit, belly, seed, peak=.45, belly_k=.34):
    """Poster cloud: a bumpy top, a flat bottom, a darker belly along the bottom. The bumps grow
    toward x0 + peak * width. Returns (defs, svg)."""
    rnd = random.Random(seed)
    w = x1 - x0
    puffs = []
    x = x0 + hgt * .2
    while x < x1 - hgt * .2:
        t = (x - x0) / w
        prof = max(0.0, 1 - abs(t - peak) / max(peak, 1 - peak)) ** .9
        r = hgt * (.34 + .44 * prof) * rnd.uniform(.85, 1.1)
        puffs.append((x, base - r * .45, r))
        x += r * rnd.uniform(1.2, 1.5)
    px = x0 + w * peak
    puffs.append((px + rnd.uniform(-.06, .06) * w, base - hgt * .58, hgt * .5))
    puffs.append((px - w * .14, base - hgt * .38, hgt * .4))
    shapes = ''.join('<circle cx="%s" cy="%s" r="%s"/>' % (f(a), f(b), f(c)) for a, b, c in puffs)
    bh = hgt * belly_k
    defs = ('<clipPath id="%sa"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>'
            '<clipPath id="%sb"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>'
            % (uid, f(x0 - 40), f(base - 3 * hgt), f(w + 80), f(3 * hgt), uid, f(x0 - 40), f(base - bh), f(w + 80), f(bh)))
    svg = ('<g clip-path="url(#%sa)" fill="%s">%s</g><g clip-path="url(#%sb)" fill="%s">%s</g>'
           % (uid, lit, shapes, uid, belly, shapes))
    return defs, svg


def streak(uid, x0, x1, base, hgt, lit, belly, bumps):
    """A long, low cloud: a smooth hump on a flat bottom with a few round bumps (t along the cloud,
    radius as a share of hgt) and a darker belly. Returns (defs, svg)."""
    w = x1 - x0
    hump = [(x0 + w * k / 40, base - hgt * .62 * math.sin(math.pi * k / 40) ** .55) for k in range(41)]
    shapes = '<path d="%s"/>' % poly(hump + [(x1, base), (x0, base)])
    shapes += ''.join('<circle cx="%s" cy="%s" r="%s"/>' % (f(x0 + w * t), f(base - hgt * k * .8), f(hgt * k)) for t, k in bumps)
    bh = hgt * .32
    defs = ('<clipPath id="%sa"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>'
            '<clipPath id="%sb"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>'
            % (uid, f(x0 - 9), f(base - 3 * hgt), f(w + 18), f(3 * hgt), uid, f(x0 - 9), f(base - bh), f(w + 18), f(bh)))
    svg = ('<g clip-path="url(#%sa)" fill="%s">%s</g><g clip-path="url(#%sb)" fill="%s">%s</g>'
           % (uid, lit, shapes, uid, belly, shapes))
    return defs, svg


def telescope(ox, oy, R, ground, el=44, az=50, detail=True, tone=None):
    """A radio telescope in two-tone flat faces: rim centre at (ox, oy), rim radius R, footing at
    screen y = ground. Light comes from the right. tone(colour) fades colours for distance.
    Returns (mount svg, dish svg, bearing point); the dish svg can turn about the bearing point."""
    tone = tone or (lambda c: c)
    el, az = math.radians(el), math.radians(az)
    n = (math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az))
    e = v_norm((n[2], 0, -n[0]))                     # horizontal: the elevation axis
    v = v_cross(n, e)
    depth = .21 * R
    foc = R * R / (4 * depth)

    def P(p):
        return (ox + p[0], oy - p[1])

    def S(r, t):                                     # reflector surface
        return v_add(v_mul(n, -depth * (1 - (r / R) ** 2)), v_mul(e, r * math.cos(t)), v_mul(v, r * math.sin(t)))

    def D(r, t):                                     # back face of the backup structure
        return v_add(S(r, t), v_mul(n, -.16 * R * (1.4 - .4 * r / R)))
    ts = [math.radians(a) for a in range(0, 360, 5)]
    rim = [P(S(R, t)) for t in ts]
    back = hull(rim + [P(D(R * k / 5, t)) for k in range(6) for t in ts])
    lip = hull(rim + [P(v_add(S(R, t), v_mul(n, -.06 * R))) for t in ts])

    lit, dark = tone(C['sunset']), tone(mix(C['sunset'], C['ink'], .45))
    bowl_lit, bowl_dark = tone(C['cream']), tone(mix(C['skyBlueLight'], C['skyBlue'], .35))
    concrete, concrete_dark = tone(mix(C['sand'], C['cream'], .3)), tone(mix(C['sand'], C['ink'], .35))

    def box(x0, y0, x1, y1, split):
        """A front face lit on the right of x = split, dark on the left."""
        return ('<path d="%s" fill="%s"/><path d="%s" fill="%s"/>'
                % (poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), dark, poly([(split, y0), (x1, y0), (x1, y1), (split, y1)]), lit))

    # mount: a fork up to the elevation bearings, a small cab, a tapered pedestal, a concrete footing
    bear = v_mul(n, -(depth + .26 * R))
    bx, by = P(bear)
    cab0 = by + .4 * R
    cab1 = cab0 + .12 * R
    mount = []
    top, bot = .19 * R, .28 * R
    mount.append('<path d="%s" fill="%s"/><path d="%s" fill="%s"/>' % (
        poly([(bx - top, cab1), (bx + top, cab1), (bx + bot, ground), (bx - bot, ground)]), dark,
        poly([(bx - top * .2, cab1), (bx + top, cab1), (bx + bot, ground), (bx - bot * .2, ground)]), lit))
    if detail:
        mount.append(box(bx - .36 * R, ground - .045 * R, bx + .36 * R, ground + .03 * R, bx - .08 * R)
                     .replace(dark, concrete_dark).replace(lit, concrete))
    arm_t, arm_b = .07 * R, .1 * R
    for sgn in (-1, 1):
        ex, ey = P(v_add(bear, v_mul(e, sgn * .3 * R)))
        lx = bx + sgn * .2 * R
        mount.append('<path d="%s" fill="%s"/>' % (poly([(ex - arm_t, ey), (ex + arm_t, ey), (lx + arm_b, cab0 + 1), (lx - arm_b, cab0 + 1)]),
                                                   lit if sgn > 0 else dark))
    mount.append(box(bx - .3 * R, cab0, bx + .32 * R, cab1, bx - .02 * R))

    # dish: backup structure and truss, lit lip, bowl with its shadow crescent, hub, quadripod, feed
    dish = ['<path d="%s" fill="%s"/>' % (poly(back), dark)]
    if detail:
        truss = []
        for i, t in enumerate(ts[::2]):
            a, b = P(S(R, t)), P(D(R * .45, t + (.1 if i % 2 else -.1)))
            truss.append('M%s %sL%s %s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])))
        dish.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (''.join(truss), lit, f(R * .011)))
        for k in (.82, .6):
            dish.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (poly([P(D(R * k, t)) for t in ts]), lit, f(R * .014)))
    dish.append('<path d="%s" fill="%s"/>' % (poly(lip), lit))
    dish.append('<path d="%s" fill="%s"/>' % (poly(rim), bowl_dark))
    uid = 'rim%d' % int(ox * 10 + oy)
    sx, sy = -.22 * R, .1 * R
    dish.append('<clipPath id="%s"><path d="%s"/></clipPath><path d="%s" fill="%s" clip-path="url(#%s)"/>'
                % (uid, poly(rim), poly([(x + sx, y + sy) for x, y in rim]), bowl_lit, uid))
    if detail:
        for k in (.66, .33):
            dish.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" opacity=".5"/>'
                        % (poly([P(S(R * k, t)) for t in ts]), bowl_dark, f(R * .011)))
        dish.append('<path d="%s" fill="%s"/>' % (poly([P(v_add(S(R * .09, t), v_mul(n, .03 * R))) for t in ts]), concrete_dark))
        dish.append('<path d="%s" fill="%s"/>' % (poly([P(v_add(S(R * .07, t), v_mul(n, .05 * R))) for t in ts]), concrete))
    apex = v_mul(n, foc - depth)
    ax, ay = P(apex)
    legs = ''.join('M%s %sL%s %s' % (f(x), f(y), f(ax), f(ay))
                   for x, y in (P(S(R * .97, math.radians(a))) for a in (45, 135, 225, 315)))
    dish.append('<path d="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (legs, dark, f(max(.45, R * .017))))
    nx_, ny_ = n[0], -n[1]
    m = math.hypot(nx_, ny_)
    ux, uy = nx_ / m, ny_ / m                        # feed axis on screen
    px, py = -uy, ux
    fw, fl = .06 * R, .15 * R
    feed = [(ax + px * fw, ay + py * fw), (ax - px * fw, ay - py * fw),
            (ax - px * fw * .65 + ux * fl, ay - py * fw * .65 + uy * fl), (ax + px * fw * .65 + ux * fl, ay + py * fw * .65 + uy * fl)]
    dish.append('<path d="%s" fill="%s"/>' % (poly(feed), lit))
    dish.append('<path d="%s" fill="%s"/>' % (poly([feed[0], (ax, ay), (ax + ux * fl, ay + uy * fl), feed[3]]), dark))
    return ''.join(mount), ''.join(dish), (bx, by)


def paper_defs():
    """Paper layer: fine grain, light fibres, low-frequency mottling, vignette."""
    return ('<filter id="pgrain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            '<feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="11" stitchTiles="stitch"/>'
            '<feColorMatrix type="matrix" values="0 0 0 0 .18 0 0 0 0 .23 0 0 0 0 .25 2.6 0 0 0 -1.3"/></filter>'
            '<filter id="pspeck" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            '<feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="1" seed="4" stitchTiles="stitch"/>'
            '<feColorMatrix type="matrix" values="0 0 0 0 .95 0 0 0 0 .87 0 0 0 0 .7 3 0 0 0 -1.8"/></filter>'
            '<filter id="pmottle" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            '<feTurbulence type="fractalNoise" baseFrequency=".03 .04" numOctaves="3" seed="21"/>'
            '<feColorMatrix type="matrix" values="0 0 0 0 .95 0 0 0 0 .87 0 0 0 0 .7 2.4 0 0 0 -1"/></filter>'
            '<filter id="fspeck" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            '<feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="1" seed="4" stitchTiles="stitch"/>'
            '<feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 3 0 0 0 -1.8"/></filter>'
            '<radialGradient id="pvig" cx=".5" cy=".46" r=".75"><stop offset=".5" stop-color="' + C['ink'] + '" stop-opacity="0"/>'
            '<stop offset="1" stop-color="' + C['ink'] + '" stop-opacity=".42"/></radialGradient>')


def paper(w, h):
    """The paper layer over the scene."""
    return ('<rect width="%s" height="%s" filter="url(#pmottle)" opacity=".16"/>'
            '<rect width="%s" height="%s" filter="url(#pgrain)" opacity=".16"/>'
            '<rect width="%s" height="%s" filter="url(#pspeck)" opacity=".28"/>'
            '<rect width="%s" height="%s" fill="url(#pvig)"/>' % ((f(w), f(h)) * 4))


def margin_paper(w, h):
    """The paper layer over the off-white margin: the same grain, pale fibres, a light vignette."""
    return ('<rect width="%s" height="%s" filter="url(#pgrain)" opacity=".13"/>'
            '<rect width="%s" height="%s" filter="url(#fspeck)" opacity=".5"/>'
            '<rect width="%s" height="%s" fill="url(#pvig)" opacity=".22"/>' % ((f(w), f(h)) * 3))


def mesa(x0, x1, base, hg, lit, shade, cap=.72):
    """A flat-topped mesa from x0 to x1 on the line base, height hg: talus slopes, short cliffs, a
    flat cap. The left face is in shade (the light comes from the right)."""
    sl = hg * .9
    pts = [(x0, base + 1), (x0 + sl * .7, base - hg * cap), (x0 + sl * .8, base - hg), (x1 - sl * .8, base - hg),
           (x1 - sl * .7, base - hg * cap), (x1, base + 1)]
    cut = x0 + sl * .8 + (x1 - x0 - 1.6 * sl) * .22
    return ('<path d="%s" fill="%s"/><path d="%s" fill="%s"/>'
            % (poly(pts), lit, poly(pts[:3] + [(cut, base - hg), (cut - hg * .5, base + 1)]), shade))


def grass(x, y, s, fill):
    """A spiky tuft of desert grass, base at (x, y), height s."""
    blades = []
    for a in (-58, -36, -16, 0, 14, 33, 55):
        r = s * (1 - abs(a) / 95)
        t = math.radians(a - 90)
        tx, ty = x + r * math.cos(t), y + r * math.sin(t)
        nx_, ny_ = -math.sin(t) * s * .07, math.cos(t) * s * .07
        blades.append('M%s %sL%s %sL%s %sZ' % (f(x - nx_ * 1.4), f(y - ny_ * 1.4), f(tx), f(ty), f(x + nx_ * 1.4), f(y + ny_ * 1.4)))
    return '<path d="%s" fill="%s"/>' % (''.join(blades), fill)


def poster_art(w, h):
    """The travel poster on a w x h card: an off-white paper margin round a flat two-tone scene."""
    M = 8.5                                          # paper margin
    aw, ah = w - 2 * M, h - 2 * M
    hz = round(ah * .7)                              # horizon
    defs = [paper_defs(), '<clipPath id="art"><rect width="%s" height="%s" rx="3"/></clipPath>' % (f(aw), f(ah)),
            '<clipPath id="artp"><rect x="%s" y="%s" width="%s" height="%s" rx="3"/></clipPath>' % (f(M), f(M), f(aw), f(ah))]
    s = []

    # sky: flat bands, deep teal at the top to a pale warm haze at the horizon
    bands = [(0, C['deepTeal']), (.3, mix(C['deepTeal'], C['reefTeal'], .5)), (.5, mix(C['reefTeal'], C['skyBlue'], .3)),
             (.64, mix(C['reefTeal'], C['skyBlue'], .68)), (.76, mix(C['skyBlue'], C['skyBlueLight'], .4)),
             (.86, C['skyBlueLight']), (.93, mix(C['skyBlueLight'], C['cream'], .6))]
    for i, (y0, col) in enumerate(bands):
        y1 = bands[i + 1][0] if i + 1 < len(bands) else 1.02
        s.append('<rect y="%s" width="%s" height="%s" fill="%s"/>' % (f(y0 * hz), f(aw), f((y1 - y0) * hz + .6), col))

    # crescent moon (earthlit disc, crescent, bright limb) and stars
    mx, my, mr = aw * .21, ah * .125, 17
    s.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(mx), f(my), f(mr), mix(C['deepTeal'], C['skyBlue'], .28)))
    s.append('<path d="%s" fill="%s"/>' % (poly(crescent(mx, my, mr, -mr * .46, -mr * .24, mr * .97)), mix(C['cream'], C['sand'], .5)))
    s.append('<path d="%s" fill="%s"/>' % (poly(crescent(mx, my, mr, -mr * .58, -mr * .3, mr * .99)), C['cream']))
    rnd = random.Random(3)
    st = []
    while len(st) < 15:
        x, y = rnd.uniform(8, aw - 8), rnd.uniform(6, hz * .44)
        if math.hypot(x - mx, y - my) < 28 or any(math.hypot(x - a, y - b) < 20 for a, b, _ in st):
            continue
        st.append((x, y, rnd.choice((1.4, 1.8, 2.2, 3.2))))
    for i, (x, y, z) in enumerate(st):
        s.append('<path class="t%d" d="%s" fill="%s"/>' % (i % 3 + 1, star4(x, y, z, .2), C['cream']))

    # launch glow: flat rings on the horizon; the rocket climbs on a thin trail
    rx_ = aw * .855
    for r_, col in ((46, mix(bands[-1][1], C['wattle'], .3)), (31, mix(C['cream'], C['wattle'], .5)), (18, C['cream'])):
        s.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(rx_), f(hz), f(r_), col))
    top = hz * .16
    tx_ = rx_ + 7                                    # the trail leans a little to the right as it climbs
    s.append('<g class="rk"><path class="trail" d="M%s %sC%s %s %s %s %s %sL%s %sC%s %s %s %s %s %sZ" fill="%s"/>'
             % (f(rx_ - 1.7), f(hz - 4), f(rx_ - 1.4), f(hz * .55), f(tx_ - 2.2), f(hz * .32), f(tx_ - .45), f(top + 6),
                f(tx_ + .45), f(top + 6), f(tx_ - 1.0), f(hz * .32), f(rx_ + 1.4), f(hz * .55), f(rx_ + 1.7), f(hz - 4), C['cream']))
    s.append('<g class="rocket"><path d="M%s %sl1.7 5.2-1.7 2.8-1.7-2.8Z" fill="%s"/><circle cx="%s" cy="%s" r="1.6" fill="%s"/></g></g>'
             % (f(tx_), f(top + 6), C['wattle'], f(tx_), f(top + 5.6), C['cream']))

    # clouds: two long high streaks, then low banks on the horizon; the right bank glows from the launch
    cool = mix(C['cream'], C['skyBlue'], .42)
    for uid, x0, x1, base, hg, bumps, cls in (('s1', aw * .6, aw * 1.08, hz * .5, 12, ((.3, .62), (.47, .5)), 'drift'),
                                             ('s2', -aw * .1, aw * .22, hz * .73, 10, ((.55, .6), (.72, .45)), 'drift d2')):
        d_, s_ = streak(uid, x0, x1, base, hg, C['cream'], cool, bumps)
        defs.append(d_)
        s.append('<g class="%s">%s</g>' % (cls, s_))
    cl = [('c3', -aw * .1, aw * .42, hz + 1, 40, C['cream'], cool, 2, .3, 'drift d2'),
          ('c4', aw * .55, aw * 1.1, hz + 1, 50, C['cream'], mix(C['cream'], C['wattle'], .55), 5, .55, 'drift')]
    for uid, x0, x1, base, hg, lit, belly, seed, peak, cls in cl:
        d_, s_ = flat_cloud(uid, x0, x1, base, hg, lit, belly, seed, peak)
        defs.append(d_)
        s.append('<g class="%s">%s</g>' % (cls, s_))

    # far mesas: pale and cool
    far_lit, far_shade = mix(C['skyBlueLight'], C['sand'], .55), mix(C['skyBlueLight'], C['skyBlue'], .55)
    s.append(mesa(-20, aw * .3, hz, 16, far_lit, far_shade))
    s.append(mesa(aw * .56, aw * 1.04, hz, 13, far_lit, far_shade))
    s.append(mesa(aw * .66, aw * .9, hz, 22, far_lit, far_shade))
    # plain: bands that warm and darken toward the viewer
    plains = [(hz, mix(C['sand'], C['skyBlueLight'], .3), 0, None),
              (hz + 8, mix(C['sand'], C['ochre'], .25), 1, (aw * .3, aw * .85, hz + 12, 4)),
              (hz + 20, mix(C['sand'], C['ochre'], .6), 2, (-aw * .2, aw * .5, hz + 27, 8)),
              (hz + 40, mix(C['ochre'], C['sand'], .1), 3, (aw * .45, aw * 1.2, hz + 50, 12)),
              (hz + 66, mix(C['ochre'], C['sunset'], .2), 4, None)]
    for i, (y0, col, amp, patch) in enumerate(plains):
        pts = [(x, y0 + amp * math.sin(x / aw * math.pi * (1.2 + i * .35) + i * 1.7)) for x in [aw * k / 24 for k in range(25)]]
        s.append('<path d="%s" fill="%s"/>' % (poly([(-1, ah + 1), (-1, pts[0][1])] + pts + [(aw + 1, pts[-1][1]), (aw + 1, ah + 1)]), col))
        if patch:                                    # a cloud shadow lying on the band
            x0, x1, yc, hg = patch
            upper = [(x0 + (x1 - x0) * k / 30, yc - hg / 2 * math.sin(math.pi * k / 30) ** .5) for k in range(31)]
            lower = [(x, yc + (yc - y) * .5) for x, y in reversed(upper)]
            s.append('<path d="%s" fill="%s"/>' % (poly(upper + lower), mix(col, C['ink'], .2)))

    # distant telescopes across the plain, paler the farther they are
    haze_col = mix(C['skyBlueLight'], C['sand'], .45)
    for x, y, r_, haze in ((aw * .05, hz + 2, 5, .72), (aw * .14, hz + 3, 6, .68), (aw * .64, hz + 3.5, 6.5, .66),
                           (aw * .78, hz + 6, 8.5, .58), (aw * .93, hz + 11, 11, .5)):
        def tone(c, haze=haze):
            return mix(c, haze_col, haze)
        m_, d_, _ = telescope(x, y - 1.5 * r_, r_, y, detail=False, tone=tone)
        s.append(m_ + d_)

    # the road from the telescope to the foreground
    R = 84
    base_y = hz + 32
    bx = aw * .4
    road_lit, road_dark = mix(C['cream'], C['sand'], .35), mix(C['sand'], C['ochre'], .35)
    road = ('M%s %sL%s %sC%s %s %s %s %s %sL%s %sC%s %s %s %s %s %sZ'
            % (f(bx - 6), f(base_y + 2), f(bx + 8), f(base_y + 2), f(bx + 22), f(base_y + 26), f(aw * .63), f(ah - 50),
               f(aw * .8), f(ah + 2), f(aw * .5), f(ah + 2), f(aw * .5), f(ah - 44), f(bx + 4), f(base_y + 24), f(bx - 6), f(base_y + 2)))
    s.append('<path d="%s" fill="%s"/>' % (road, road_dark))
    s.append('<path d="%s" fill="%s"/>' % (road.replace(f(aw * .5), f(aw * .56), 1), road_lit))

    # the big telescope: its flat shadow thrown left, the mount, the dish turning slowly on its bearing
    mount, dish, (px, py) = telescope(bx, base_y - 1.66 * R, R, base_y)
    sh = mix(plains[2][1], C['ink'], .38)
    s.append('<path d="%s" fill="%s"/>' % (poly([(bx + .25 * R, base_y + 2), (bx - .25 * R, base_y - 3), (bx - 1.15 * R, base_y + 4),
                                                  (bx - 1.0 * R, base_y + 10)]), sh))
    s.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>' % (f(bx - 1.25 * R), f(base_y + 7), f(.5 * R), f(.075 * R), sh))
    s.append(mount)
    s.append('<g class="nod" style="transform-origin:%spx %spx">%s</g>' % (f(px), f(py), dish))

    # foreground: a dark rise in each bottom corner with grass tufts, framing the road
    fg, fg_dark = mix(C['sunset'], C['ink'], .4), mix(C['sunset'], C['ink'], .58)
    left = [(-1, ah - 62), (aw * .14, ah - 52), (aw * .3, ah - 30), (aw * .46, ah + 1), (-1, ah + 1)]
    right = [(aw + 1, ah - 40), (aw * .9, ah - 34), (aw * .82, ah - 14), (aw * .78, ah + 1), (aw + 1, ah + 1)]
    s.append('<path d="%s" fill="%s"/><path d="%s" fill="%s"/>' % (poly(left), fg, poly(right), fg))
    s.append('<path d="%s" fill="%s"/>' % (poly([(-1, ah - 30), (aw * .12, ah - 22), (aw * .3, ah + 1), (-1, ah + 1)]), fg_dark))
    rnd = random.Random(12)
    for x, y, z in ((aw * .03, ah - 60, 14), (aw * .12, ah - 52, 10), (aw * .22, ah - 41, 12), (aw * .32, ah - 24, 9),
                    (aw * .4, ah - 9, 11), (aw * .86, ah - 31, 10), (aw * .95, ah - 38, 13), (aw * .07, ah - 26, 16)):
        s.append(grass(x, y + 2, z * rnd.uniform(.9, 1.1), fg if y > ah - 28 and x < aw * .2 else fg_dark))

    body = ('<rect width="%s" height="%s" fill="%s"/>' % (f(w), f(h), FRAME) + margin_paper(w, h) +
            '<g transform="translate(%s %s)"><g clip-path="url(#art)">%s</g></g>' % (f(M), f(M), ''.join(s)) +
            '<g clip-path="url(#artp)">%s</g>' % paper(w, h))
    css = (TWINKLE +
           '.drift{animation:drift 14s ease-in-out infinite alternate}.d2{animation-duration:11s;animation-direction:alternate-reverse}'
           '@keyframes drift{from{transform:translateX(-5px)}to{transform:translateX(5px)}}'
           '.nod{animation:nod 12s ease-in-out infinite alternate}'
           '@keyframes nod{from{transform:rotate(-1.4deg)}to{transform:rotate(1deg)}}'
           '.trail{transform-box:fill-box;transform-origin:50% 100%;animation:trail 13s cubic-bezier(.4,0,.6,1) infinite}'
           '@keyframes trail{0%{transform:scaleY(0)}70%{transform:scaleY(1)}100%{transform:scaleY(1)}}'
           '.rocket{animation:climb 13s cubic-bezier(.4,0,.6,1) infinite}'
           '@keyframes climb{0%{transform:translate(XOFFpx,RISEpx)}70%{transform:translate(0,0)}100%{transform:translate(0,0)}}'
           '.rk{animation:fade 13s linear infinite}'
           '@keyframes fade{0%{opacity:0}6%{opacity:1}82%{opacity:1}100%{opacity:0}}').replace('RISE', f(hz - top - 10)).replace('XOFF', f(rx_ - tx_))
    return css, ''.join(defs), body


# ---------------------------------------------------------------- the pile

# depth: offset of the bottom card from the top card (left, down), px. cards: cards under the top
# one. foot: clear strip under the pile for its shadow. bulge: extra left shift of the middle of
# the stack. loose: (card number from the top, dx, dy, turn in degrees) of the cards off line.
# rim: offset of the top card's own edge (left, down).
PILE = dict(depth=(10, 28), cards=38, foot=3, bulge=1.2, rim=(.3, .85),
            loose=((5, -1.2, .2, .3), (14, .6, -.1, -.4), (22, -1.9, .6, .26), (29, .4, .5, -.32), (34, -1, .3, .16)))
STOCK = mix(FRAME, '#cdc9c2', .3)                    # off-white card stock seen edge-on
SHADE = mix(C['ink'], '#a39584', .45)               # neutral grey shade on the card edges
GAP = mix(STOCK, SHADE, .72)                         # hairline between two cards
SHADOW = {'light': (.26, .38), 'dark': (.55, .7)}    # opacity of the soft shadow and the contact line


def pile(theme, aria, title):
    """The draw pile: contact shadow, the stacked cards, the top card with poster_art clipped to it."""
    L = LAYOUT['wide']
    cw, ch, r = L['cw'], L['ch'], L['r']
    dx, dy = PILE['depth']
    n = PILE['cards']
    tw, th = cw - dx, ch - PILE['foot'] - dy         # top card size; it sits at (0, 0)
    css, adefs, body = poster_art(tw, th)
    rnd = random.Random(7)

    # depth of each card under the top one, 0 < t <= 1, in uneven steps
    steps = [rnd.uniform(.75, 1.25) for _ in range(n)]
    t, ts = 0.0, []
    for s_ in steps:
        t += s_
        ts.append(t / sum(steps))
    loose = {k: (a, b, c) for k, a, b, c in PILE['loose']}
    clumps = set(rnd.sample(range(2, n - 1), 5))

    cards, clip = [], []
    for k in range(n, 0, -1):                        # bottom card first
        t = ts[k - 1]
        ox = -dx * t - PILE['bulge'] * math.sin(math.pi * t) + rnd.uniform(-.12, .12)
        oy = dy * t
        a, b, turn = loose.get(k, (0, 0, 0))
        ox, oy = ox + a, oy + b
        rot = (' transform="rotate(%s %s %s)"' % (f(turn), f(ox + tw / 2), f(oy + th / 2))) if turn else ''
        shade = .32 + .46 * t ** 1.15 + rnd.uniform(-.05, .05) - (.1 if k in loose else 0)
        line_w, line_op = (.42, .95) if k in clumps else (.26, rnd.uniform(.45, .8))
        geo = 'x="%s" y="%s" width="%s" height="%s" rx="%s"%s' % (f(ox), f(oy), f(tw), f(th), f(r), rot)
        cards.append('<rect %s fill="%s" stroke="%s" stroke-width="%s" stroke-opacity="%s"/>'
                     % (geo, mix(STOCK, SHADE, shade), GAP, f(line_w), f(line_op)))
        clip.append('<rect %s/>' % geo)
    # the top card's own edge: pale, over a dark gap
    rx_, ry_ = PILE['rim']
    rim = ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width=".6"/>'
           % (f(-rx_), f(ry_), f(tw), f(th), f(r), mix(STOCK, '#ffffff', .35), GAP))

    def stops(x0, x1, pts):
        return ''.join('<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % (f((x - x0) / (x1 - x0)), c, f(o))
                       for x, c, o in pts)
    # pside, clipped to the cards: shade over the left face that fades out across the bottom-left
    # corners, and a light lift where the front face turns toward the light at the bottom right
    x0, x1 = -dx - 2, tw
    soft, contact = SHADOW[theme]
    base = (-dx, dy)                                 # bottom card
    defs = (
        '<filter id="psh1" x="-10%%" y="-10%%" width="120%%" height="120%%"><feGaussianBlur stdDeviation="3"/></filter>'
        '<filter id="psh2" x="-5%%" y="-5%%" width="110%%" height="110%%"><feGaussianBlur stdDeviation="1"/></filter>'
        '<linearGradient id="pfadeg" gradientUnits="userSpaceOnUse" x1="0" y1="%s" x2="0" y2="%s">'
        '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<mask id="pfade" maskUnits="userSpaceOnUse" x="%s" y="0" width="%s" height="%s">'
        '<rect x="%s" width="%s" height="%s" fill="url(#pfadeg)"/></mask>'
        % (f(ch - PILE['foot'] - .5), f(ch), f(x0 - 30), f(cw + 60), f(ch), f(x0 - 30), f(cw + 60), f(ch)) +
        '<linearGradient id="pside" gradientUnits="userSpaceOnUse" x1="%s" y1="0" x2="%s" y2="0">%s</linearGradient>'
        % (f(x0), f(x1), stops(x0, x1, [(x0, SHADE, .5), (-.5, SHADE, .36), (11, SHADE, 0),
                                         (tw - 18, '#fff', 0), (tw, '#fff', .16)])) +
        '<linearGradient id="prim" gradientUnits="userSpaceOnUse" x1="0" y1="%s" x2="%s" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity=".3"/><stop offset="1" stop-color="#fff" stop-opacity=".7"/>'
        '</linearGradient>' % (f(th), f(tw)) +
        '<clipPath id="pstack">%s</clipPath>' % ''.join(clip) +
        '<clipPath id="tc"><rect width="%s" height="%s" rx="%s"/></clipPath>' % (f(tw), f(th), f(r)) + adefs)
    out = [
        '<g mask="url(#pfade)" fill="#000">'
        '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" opacity="%s" filter="url(#psh1)"/>'
        '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" opacity="%s" filter="url(#psh2)"/></g>'
        % (f(base[0] - 5), f(base[1] + 1.5), f(tw), f(th), f(r), f(soft),
           f(base[0] - .8), f(base[1] + .6), f(tw), f(th), f(r), f(contact)),
        ''.join(cards),
        '<rect x="%s" width="%s" height="%s" fill="url(#pside)" clip-path="url(#pstack)"/>' % (f(x0), f(x1 - x0), f(ch)),
        rim,
        '<g clip-path="url(#tc)">%s</g>' % body,
        '<rect x=".35" y=".35" width="%s" height="%s" rx="%s" fill="none" stroke="url(#prim)" stroke-width=".7"/>'
        % (f(tw - .7), f(th - .7), f(r - .35)),
    ]
    off = L['slot'] - cw
    head = svg_open(-off - dx, L['slot'], ch, L['slot'], ch, aria, title, css + REDUCE, defs)
    return head + ''.join(out) + '</svg>\n'


ARIA = 'Draw pile of face-down cards: a retro travel poster of a radio telescope under a crescent moon'

if __name__ == '__main__':
    OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2] / 'assets'
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        out = OUT / ('card-back-%s.svg' % theme)
        out.write_text(pile(theme, ARIA, 'Draw pile'), encoding='utf-8')
        print(out.name, out.stat().st_size)
