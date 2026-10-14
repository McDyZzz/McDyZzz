"""The page's 5 x 7 pixel font: the same glyphs as the header's typing banner.
Lowercase, digits and '-' here; drawn in code, no font file.

GLYPHS: rows from the top, '#' = lit cell. Rows 0-6 sit on the baseline (row 6 is the last row
above it); rows 7-8 hold descenders.
layout(text): proportional spacing. Each glyph's empty side columns are trimmed, then it advances
by its width plus GAP cells; a space is SPACE cells wide.
path(text, cell, x, y): SVG path data of the lit cells, `cell` px per cell, top of the 7-row box at
y, left edge at x. Returns (path data, width in px).
"""

GAP = 1
SPACE = 3

GLYPHS = {
    'a': ".....|.....|.###.|....#|.####|#...#|.####",
    'b': "#....|#....|#.##.|##..#|#...#|#...#|####.",
    'c': ".....|.....|.####|#....|#....|#....|.####",
    'd': "....#|....#|.##.#|#..##|#...#|#...#|.####",
    'e': ".....|.....|.###.|#...#|#####|#....|.####",
    'f': "..###|.#...|####.|.#...|.#...|.#...|.#...",
    'g': ".....|.....|.####|#...#|#...#|#...#|.####|....#|.###.",
    'h': "#....|#....|#.##.|##..#|#...#|#...#|#...#",
    'i': ".#.|...|##.|.#.|.#.|.#.|###",
    'j': "..#|...|.##|..#|..#|..#|..#|#.#|.#.",
    'k': "#....|#....|#..#.|#.#..|##...|#.#..|#..#.",
    'l': "##.|.#.|.#.|.#.|.#.|.#.|###",
    'm': ".....|.....|##.#.|#.#.#|#.#.#|#...#|#...#",
    'n': ".....|.....|#.##.|##..#|#...#|#...#|#...#",
    'o': ".....|.....|.###.|#...#|#...#|#...#|.###.",
    'p': ".....|.....|####.|#...#|#...#|#...#|####.|#....|#....",
    'q': ".....|.....|.####|#...#|#...#|#...#|.####|....#|....#",
    'r': ".....|.....|#.##.|##..#|#....|#....|#....",
    's': ".....|.....|.####|#....|.###.|....#|####.",
    't': ".#...|.#...|####.|.#...|.#...|.#...|..##.",
    'u': ".....|.....|#...#|#...#|#...#|#..##|.##.#",
    'v': ".....|.....|#...#|#...#|#...#|.#.#.|..#..",
    'w': ".....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.",
    'x': ".....|.....|#...#|.#.#.|..#..|.#.#.|#...#",
    'y': ".....|.....|#...#|#...#|#...#|#...#|.####|....#|.###.",
    'z': ".....|.....|#####|...#.|..#..|.#...|#####",
    '-': ".....|.....|.....|.###.",
    '0': ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    '1': ".#.|##.|.#.|.#.|.#.|.#.|###",
    '2': ".###.|#...#|....#|...#.|..#..|.#...|#####",
    '3': "####.|....#|....#|.###.|....#|....#|####.",
    '4': "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    '5': "#####|#....|####.|....#|....#|#...#|.###.",
    '6': ".###.|#....|#....|####.|#...#|#...#|.###.",
    '7': "#####|....#|...#.|..#..|.#...|.#...|.#...",
    '8': ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    '9': ".###.|#...#|#...#|.####|....#|....#|.###.",
}


def cells(ch):
    """Lit cells (x, y) of a glyph with its empty side columns trimmed, and its width."""
    rows = GLYPHS[ch].split('|')
    lit = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == '#']
    x0 = min(x for x, _ in lit)
    x1 = max(x for x, _ in lit)
    return [(x - x0, y) for x, y in lit], x1 - x0 + 1


def layout(text):
    """Lit cells of the whole line, and its width in cells."""
    out, x = [], 0
    for i, ch in enumerate(text):
        if ch == ' ':
            x += SPACE
            continue
        lit, w = cells(ch)
        out += [(x + cx, cy) for cx, cy in lit]
        x += w + (GAP if i < len(text) - 1 else 0)
    return out, x


def runs(lit):
    """Cover lit cells with rectangles: horizontal runs per row, merged down when equal."""
    rows = {}
    for x, y in lit:
        rows.setdefault(y, set()).add(x)
    spans = []
    for y in sorted(rows):
        xs = sorted(rows[y])
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            spans.append([start, y, prev - start + 1, 1])
            if x is not None:
                start = prev = x
    merged = []
    for s in spans:
        for m in merged:
            if m[0] == s[0] and m[2] == s[2] and m[1] + m[3] == s[1]:
                m[3] += 1
                break
        else:
            merged.append(s)
    return merged


def fmt(v):
    s = ('%.3f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def path(text, cell, x=0, y=0):
    lit, w = layout(text)
    d = ''.join('M%s %sh%sv%sh-%sz' % (fmt(x + rx * cell), fmt(y + ry * cell), fmt(rw * cell), fmt(rh * cell), fmt(rw * cell))
                for rx, ry, rw, rh in runs(lit))
    return d, w * cell
