"""Minimal TrueType reader: turns text into SVG glyph paths (cmap, glyf, hmtx, GPOS pair kerning).

Variable fonts: TTF(path, wght=600) builds that instance from fvar, avar and gvar (glyph outlines,
advance widths through the phantom points). GPOS kerning stays at the default instance.
A static font ignores the axis values.
"""
import struct


class TTF:
    def __init__(self, path, **axes):
        d = self.d = open(path, 'rb').read()
        n = struct.unpack('>H', d[4:6])[0]
        self.t = {}
        for i in range(n):
            tag, _, off, ln = struct.unpack('>4sIII', d[12 + 16 * i:28 + 16 * i])
            self.t[tag.decode('latin1')] = off
        h = self.t['head']
        self.upm = self.u16(h + 18)
        locfmt = self.s16(h + 50)
        self.n = self.u16(self.t['maxp'] + 4)
        nhm = self.u16(self.t['hhea'] + 34)
        hm = self.t['hmtx']
        self.adv = [self.u16(hm + 4 * min(i, nhm - 1)) for i in range(self.n)]
        lo = self.t['loca']
        if locfmt == 0:
            self.loca = [2 * self.u16(lo + 2 * i) for i in range(self.n + 1)]
        else:
            self.loca = [self.u32(lo + 4 * i) for i in range(self.n + 1)]
        self.cmap = self._cmap()
        self.kern = {}
        self._cls = []
        if 'GPOS' in self.t:
            try:
                self._gpos()
            except Exception:
                self.kern = {}
        os2 = self.t.get('OS/2')
        self.cap = (self.s16(os2 + 88) if os2 and self.u16(os2) >= 2 else int(.7 * self.upm)) / self.upm
        self.norm = None
        self._dcache = {}
        if axes and 'fvar' in self.t and 'gvar' in self.t:
            self._setup_instance(axes)
            self.adv = [self.adv[g] + self._adv_delta(g) for g in range(self.n)]

    def u16(self, o): return struct.unpack('>H', self.d[o:o + 2])[0]
    def s16(self, o): return struct.unpack('>h', self.d[o:o + 2])[0]
    def u32(self, o): return struct.unpack('>I', self.d[o:o + 4])[0]

    def _cmap(self):
        c = self.t['cmap']
        best = None
        for i in range(self.u16(c + 2)):
            pid, eid, off = struct.unpack('>HHI', self.d[c + 4 + 8 * i:c + 12 + 8 * i])
            fmt = self.u16(c + off)
            if fmt == 4 and pid in (0, 3):
                best = c + off
        o = best
        seg = self.u16(o + 6) // 2
        ends = o + 14
        starts = ends + 2 * seg + 2
        deltas = starts + 2 * seg
        ranges = deltas + 2 * seg
        m = {}
        for s in range(seg):
            e, st = self.u16(ends + 2 * s), self.u16(starts + 2 * s)
            dl, ro = self.u16(deltas + 2 * s), self.u16(ranges + 2 * s)
            for ch in range(st, e + 1):
                if ch == 0xFFFF:
                    continue
                if ro == 0:
                    g = (ch + dl) & 0xFFFF
                else:
                    a = ranges + 2 * s + ro + 2 * (ch - st)
                    g = self.u16(a)
                    if g:
                        g = (g + dl) & 0xFFFF
                m[ch] = g
        return m

    # --- GPOS pair kerning (lookup type 2, also via extension type 9) ---
    def _coverage(self, o):
        fmt = self.u16(o)
        cov = {}
        if fmt == 1:
            for i in range(self.u16(o + 2)):
                cov[self.u16(o + 4 + 2 * i)] = i
        else:
            for i in range(self.u16(o + 2)):
                s, e, si = struct.unpack('>HHH', self.d[o + 4 + 6 * i:o + 10 + 6 * i])
                for g in range(s, e + 1):
                    cov[g] = si + g - s
        return cov

    def _classdef(self, o):
        fmt = self.u16(o)
        cd = {}
        if fmt == 1:
            st = self.u16(o + 2)
            for i in range(self.u16(o + 4)):
                cd[st + i] = self.u16(o + 6 + 2 * i)
        else:
            for i in range(self.u16(o + 2)):
                s, e, c = struct.unpack('>HHH', self.d[o + 4 + 6 * i:o + 10 + 6 * i])
                for g in range(s, e + 1):
                    cd[g] = c
        return cd

    def _vsize(self, f):
        return 2 * bin(f).count('1')

    def _xadv(self, o, f):
        # returns XAdvance from a ValueRecord at o with format f
        off = 2 * bin(f & 3).count('1')      # XPlacement and YPlacement come before XAdvance
        return self.s16(o + off) if f & 4 else 0

    def _gpos(self):
        g = self.t['GPOS']
        ll = g + self.u16(g + 8)
        for li in range(self.u16(ll)):
            lk = ll + self.u16(ll + 2 + 2 * li)
            typ = self.u16(lk)
            for si in range(self.u16(lk + 4)):
                st = lk + self.u16(lk + 6 + 2 * si)
                t = typ
                if t == 9:
                    t = self.u16(st + 2)
                    st = st + self.u32(st + 4)
                if t != 2:
                    continue
                fmt = self.u16(st)
                cov = self._coverage(st + self.u16(st + 2))
                f1, f2 = self.u16(st + 4), self.u16(st + 6)
                s1, s2 = self._vsize(f1), self._vsize(f2)
                if fmt == 1:
                    for g1, ci in cov.items():
                        ps = st + self.u16(st + 10 + 2 * ci)
                        for k in range(self.u16(ps)):
                            r = ps + 2 + k * (2 + s1 + s2)
                            g2 = self.u16(r)
                            v = self._xadv(r + 2, f1)
                            if v and (g1, g2) not in self.kern:
                                self.kern[(g1, g2)] = v
                elif fmt == 2:
                    cd1 = self._classdef(st + self.u16(st + 8))
                    cd2 = self._classdef(st + self.u16(st + 10))
                    n1, n2 = self.u16(st + 12), self.u16(st + 14)
                    rec = s1 + s2
                    self._cls.append((cov, cd1, cd2, n2, st + 16, rec, f1))

    def kern_pair(self, a, b):
        if (a, b) in self.kern:
            return self.kern[(a, b)]
        for cov, cd1, cd2, n2, base, rec, f1 in self._cls:
            if a in cov:
                c1 = cd1.get(a, 0)
                c2 = cd2.get(b, 0)
                v = self._xadv(base + (c1 * n2 + c2) * rec, f1)
                if v:
                    return v
                return 0
        return 0

    # --- variable font instancing (fvar, avar, gvar) ---
    def _setup_instance(self, axes):
        o = self.t['fvar']
        aoff, ac, asz = self.u16(o + 4), self.u16(o + 8), self.u16(o + 10)
        norm = []
        for i in range(ac):
            a = o + aoff + i * asz
            tag = self.d[a:a + 4].decode('latin1')
            mn, df, mx = [struct.unpack('>i', self.d[a + 4 + 4 * k:a + 8 + 4 * k])[0] / 65536 for k in range(3)]
            v = min(max(float(axes.get(tag, df)), mn), mx)
            norm.append((v - df) / (df - mn) if v < df else ((v - df) / (mx - df) if v > df else 0.0))
        if 'avar' in self.t:
            p = self.t['avar'] + 8
            for i in range(ac):
                cnt = self.u16(p)
                pairs = [(self.s16(p + 2 + 4 * k) / 16384, self.s16(p + 4 + 4 * k) / 16384) for k in range(cnt)]
                p += 2 + 4 * cnt
                v = norm[i]
                for (f0, t0), (f1, t1) in zip(pairs, pairs[1:]):
                    if f0 <= v <= f1:
                        norm[i] = t0 if f1 == f0 else t0 + (v - f0) * (t1 - t0) / (f1 - f0)
                        break
        self.norm = norm
        g = self.t['gvar']
        self.g_axes = self.u16(g + 4)
        nshared, soff = self.u16(g + 6), self.u32(g + 8)
        self.g_shared = [[self.s16(g + soff + 2 * (k * self.g_axes + a)) / 16384 for a in range(self.g_axes)]
                         for k in range(nshared)]
        flags, doff = self.u16(g + 14), self.u32(g + 16)
        if flags & 1:
            self.g_off = [g + doff + self.u32(g + 20 + 4 * i) for i in range(self.n + 1)]
        else:
            self.g_off = [g + doff + 2 * self.u16(g + 20 + 2 * i) for i in range(self.n + 1)]

    def _scalar(self, peak, start, end):
        s = 1.0
        for v, p, a, b in zip(self.norm, peak, start, end):
            if p == 0:
                continue
            if v == p:
                continue
            if v <= a or v >= b:
                return 0.0
            s *= (v - a) / (p - a) if v < p else (b - v) / (b - p)
        return s

    def _points(self, p):
        """Packed point numbers at p; returns (list or None for all points, new p)."""
        c = self.d[p]; p += 1
        if c == 0:
            return None, p
        if c & 0x80:
            c = ((c & 0x7F) << 8) | self.d[p]; p += 1
        pts, last = [], 0
        while len(pts) < c:
            ctl = self.d[p]; p += 1
            run = (ctl & 0x7F) + 1
            for _ in range(run):
                if ctl & 0x80:
                    last += self.u16(p); p += 2
                else:
                    last += self.d[p]; p += 1
                pts.append(last)
        return pts, p

    def _deltas(self, p, n):
        out = []
        while len(out) < n:
            ctl = self.d[p]; p += 1
            run = (ctl & 0x3F) + 1
            if ctl & 0x80:
                out.extend([0] * run)
            elif ctl & 0x40:
                out.extend(self.s16(p + 2 * k) for k in range(run)); p += 2 * run
            else:
                out.extend(struct.unpack('>%db' % run, self.d[p:p + run])); p += run
        return out, p

    def _tuples(self, gid, npts):
        """Yields (scalar, {point: (dx, dy)}) for each gvar tuple of gid; npts includes the 4 phantom points."""
        o, e = self.g_off[gid], self.g_off[gid + 1]
        if e <= o:
            return
        cnt = self.u16(o)
        shared_pts = cnt & 0x8000
        cnt &= 0x0FFF
        data = o + self.u16(o + 2)
        h = o + 4
        heads = []
        for _ in range(cnt):
            size, idx = self.u16(h), self.u16(h + 2); h += 4
            if idx & 0x8000:
                peak = [self.s16(h + 2 * a) / 16384 for a in range(self.g_axes)]; h += 2 * self.g_axes
            else:
                peak = self.g_shared[idx & 0x0FFF]
            if idx & 0x4000:
                start = [self.s16(h + 2 * a) / 16384 for a in range(self.g_axes)]; h += 2 * self.g_axes
                end = [self.s16(h + 2 * a) / 16384 for a in range(self.g_axes)]; h += 2 * self.g_axes
            else:
                start = [min(0.0, v) for v in peak]
                end = [max(0.0, v) for v in peak]
            heads.append((size, idx, peak, start, end))
        p = data
        common = None
        if shared_pts:
            common, p = self._points(p)
        for size, idx, peak, start, end in heads:
            q = p
            p += size
            sc = self._scalar(peak, start, end)
            if sc == 0:
                continue
            pts = common
            if idx & 0x2000:
                pts, q = self._points(q)
            if pts is None:
                pts = list(range(npts))
            xs, q = self._deltas(q, len(pts))
            ys, q = self._deltas(q, len(pts))
            yield sc, {pt: (dx, dy) for pt, dx, dy in zip(pts, xs, ys)}

    def _glyph_deltas(self, gid, orig, ends):
        """Summed (dx, dy) per point (outline points then 4 phantom points), with IUP for simple glyphs.
        orig: default (x, y) per outline point; ends: contour end indices, or None for a composite."""
        key = gid
        if key in self._dcache:
            return self._dcache[key]
        n = len(orig)
        tot = [[0.0, 0.0] for _ in range(n + 4)]
        for sc, dd in self._tuples(gid, n + 4):
            full = dict(dd)
            if ends is not None and len([k for k in dd if k < n]) < n:
                s = 0
                for en in ends:
                    idx = list(range(s, en + 1))
                    touched = [i for i in idx if i in dd]
                    if touched and len(touched) < len(idx):
                        for i in idx:
                            if i in dd:
                                continue
                            if len(touched) == 1:
                                full[i] = dd[touched[0]]
                                continue
                            prv = max((t for t in touched if t < i), default=touched[-1])
                            nxt = min((t for t in touched if t > i), default=touched[0])
                            full[i] = tuple(_iup(orig[i][c], orig[prv][c], orig[nxt][c], dd[prv][c], dd[nxt][c])
                                            for c in (0, 1))
                    s = en + 1
            for k, (dx, dy) in full.items():
                if k < n + 4:
                    tot[k][0] += sc * dx
                    tot[k][1] += sc * dy
        self._dcache[key] = tot
        return tot

    def _adv_delta(self, gid):
        if not self.norm:
            return 0
        info = self._raw(gid)
        if info is None:
            n, ends = 0, None
            orig = []
        elif info[0] == 'simple':
            orig = [(x, y) for c in info[1] for x, y, _ in c]
            n = len(orig)
            ends = info[2]
        else:
            orig = [(0, 0)] * len(info[1])
            ends = None
        d = self._glyph_deltas(gid, orig, ends)
        m = len(orig)
        return round(d[m + 1][0] - d[m][0])

    def _raw(self, gid):
        """Default outline: ('simple', contours, ends) or ('composite', [(gid, dx, dy, flags)]) or None."""
        gl = self.t['glyf']
        o, e = gl + self.loca[gid], gl + self.loca[gid + 1]
        if e == o:
            return None
        nc = self.s16(o)
        if nc >= 0:
            ends = [self.u16(o + 10 + 2 * i) for i in range(nc)]
            npts = ends[-1] + 1 if ends else 0
            p = o + 10 + 2 * nc
            p += 2 + self.u16(p)
            flags = []
            while len(flags) < npts:
                f = self.d[p]; p += 1
                flags.append(f)
                if f & 8:
                    r = self.d[p]; p += 1
                    flags.extend([f] * r)
            flags = flags[:npts]
            xs, ys = [], []
            for arr, short, same in ((xs, 2, 16), (ys, 4, 32)):
                v = 0
                for f in flags:
                    if f & short:
                        dv = self.d[p]; p += 1
                        v += dv if f & same else -dv
                    elif not f & same:
                        v += self.s16(p); p += 2
                    arr.append(v)
            out, s = [], 0
            for en in ends:
                out.append([(xs[i], ys[i], flags[i] & 1) for i in range(s, en + 1)])
                s = en + 1
            return ('simple', out, ends)
        comps = []
        p = o + 10
        while True:
            fl, gi = self.u16(p), self.u16(p + 2); p += 4
            if fl & 1:
                dx, dy = self.s16(p), self.s16(p + 2); p += 4
            else:
                dx, dy = struct.unpack('>bb', self.d[p:p + 2]); p += 2
            if fl & 8: p += 2
            elif fl & 0x40: p += 4
            elif fl & 0x80: p += 8
            comps.append((gi, dx, dy, fl))
            if not fl & 0x20:
                break
        return ('composite', comps)

    # --- glyph outlines ---
    def contours(self, gid):
        """Outline contours [(x, y, on_curve)], at the instance when one is set."""
        info = self._raw(gid)
        if info is None:
            return []
        if info[0] == 'simple':
            cons, ends = info[1], info[2]
            if not self.norm:
                return cons
            orig = [(x, y) for c in cons for x, y, _ in c]
            d = self._glyph_deltas(gid, orig, ends)
            m = len(orig)
            ox = d[m][0]                      # phantom point 1 moves the origin
            out, k = [], 0
            for c in cons:
                out.append([(x + d[k + i][0] - ox, y + d[k + i][1], on) for i, (x, y, on) in enumerate(c)])
                k += len(c)
            return out
        comps = info[1]
        d = self._glyph_deltas(gid, [(0, 0)] * len(comps), None) if self.norm else None
        out = []
        for i, (gi, dx, dy, fl) in enumerate(comps):
            if d:
                dx, dy = dx + d[i][0] - d[len(comps)][0], dy + d[i][1]
            for c in self.contours(gi):
                out.append([(x + dx, y + dy, on) for x, y, on in c])
        return out

    def glyph_d(self, gid):
        """SVG path data in font units, y flipped (y down)."""
        parts = []
        for c in self.contours(gid):
            pts = [(x, -y, on) for x, y, on in c]
            if not pts:
                continue
            # start at an on-curve point
            si = next((i for i, p in enumerate(pts) if p[2]), None)
            if si is None:
                a, b = pts[0], pts[1]
                pts.insert(0, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1))
                si = 0
            pts = pts[si:] + pts[:si]
            cur = pts[0]
            seg = ['M%s %s' % (fmt(cur[0]), fmt(cur[1]))]
            ring = pts[1:] + [pts[0]]
            ctrl = None
            for p in ring:
                if p[2]:
                    if ctrl is None:
                        seg.append('L%s %s' % (fmt(p[0]), fmt(p[1])))
                    else:
                        seg.append('Q%s %s %s %s' % (fmt(ctrl[0]), fmt(ctrl[1]), fmt(p[0]), fmt(p[1])))
                        ctrl = None
                else:
                    if ctrl is not None:
                        mx, my = (ctrl[0] + p[0]) / 2, (ctrl[1] + p[1]) / 2
                        seg.append('Q%s %s %s %s' % (fmt(ctrl[0]), fmt(ctrl[1]), fmt(mx), fmt(my)))
                    ctrl = p
            seg.append('Z')
            parts.append(''.join(seg))
        return ''.join(parts)

    def gid(self, ch):
        return self.cmap.get(ord(ch), 0)

    def layout(self, text, tracking=0):
        """List of (gid, x_in_font_units); returns (items, total_advance)."""
        x, items, prev = 0, [], None
        for ch in text:
            g = self.gid(ch)
            if prev is not None:
                x += self.kern_pair(prev, g)
            items.append((g, x))
            x += self.adv[g] + tracking
            prev = g
        return items, x - tracking


def fmt(v):
    v = round(v)
    return str(int(v))


def _iup(x, x1, x2, d1, d2):
    """Interpolates an untouched point's delta from its two touched neighbours (gvar IUP)."""
    if x1 > x2:
        x1, x2, d1, d2 = x2, x1, d2, d1
    if x1 == x2:
        return d1 if d1 == d2 else 0
    if x <= x1:
        return d1
    if x >= x2:
        return d2
    return d1 + (x - x1) * (d2 - d1) / (x2 - x1)
