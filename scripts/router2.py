#!/usr/bin/python3
"""Grid maze router (A* on 2 outer signal layers + through vias, inner layers = solid GND).
Windowed search so it scales to a 65 x 95 mm board. Width classes with neck-down at fine-pitch pads.
usage: router2.py <cfg.py> ; the cfg defines BOARD, W, L, OX, OY, WIDTH, RULES(cost fn), ORDER_FIRST, OUTJSON"""
import pcbnew, heapq, math, sys, json, time
import numpy as np
from pcbnew import ToMM

cfg = {}
exec(open(sys.argv[1]).read(), cfg)
W, L, OX, OY = cfg["W"], cfg["L"], cfg["OX"], cfg["OY"]
G = 0.05
NX, NY = int(round(W / G)) + 1, int(round(L / G)) + 1
N = NX * NY
CLR, MARGIN = 0.15, 0.02
HALVES = tuple(cfg.get("HALVES", (0.075, 0.15, 0.25)))
INFL = max(HALVES) + CLR + MARGIN
VIA_D, VIA_DRILL = cfg.get("VIA", (0.5, 0.25))
EDGE = 0.35
NECK = 0.9
NL = cfg.get("NLAYERS", 2)          # 0 = F.Cu, 1 = B.Cu, 2 = In2.Cu (power routing layer)
def allowed(n): return cfg["layers"](n) if "layers" in cfg else (0, 1)          # within this distance of its own pad, a wide net necks down to 0.15 mm
def wid(n): return cfg["WIDTH"].get(n, 0.15)
def half(n): return wid(n) / 2
PAIRS = cfg.get("PAIRS", [])
PAIR_N = {nn: pp for pp, nn in PAIRS}
PAIR_P = {pp: nn for pp, nn in PAIRS}
PAIR_PITCH = cfg.get("PAIR_PITCH", 0.35)
xs = np.arange(NX) * G; ys = np.arange(NY) * G
XX, YY = np.meshgrid(xs, ys)

def win(x0, y0, x1, y1):
    i0, i1 = max(0, int(math.floor(x0 / G))), min(NX, int(math.ceil(x1 / G)) + 1)
    j0, j1 = max(0, int(math.floor(y0 / G))), min(NY, int(math.ceil(y1 / G)) + 1)
    return slice(j0, j1), slice(i0, i1)
def rect_dist(x0, y0, x1, y1, sl):
    X, Y = XX[sl], YY[sl]
    dx = np.maximum(np.maximum(x0 - X, X - x1), 0); dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
    return np.hypot(dx, dy)
def seg_dist(ax, ay, bx, by, sl):
    X, Y = XX[sl], YY[sl]
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1) if L2 > 0 else 0
    return np.hypot(X - (ax + t * vx), Y - (ay + t * vy))

class Router:
    def __init__(self, board):
        self.board = board
        self.OWN = {h: [np.zeros((NY, NX), np.int32) for _ in range(NL)] for h in HALVES}
        self.novia = np.zeros((NY, NX), bool)          # True = via forbidden
        self.netid, self.netname = {}, {}
        for name, ni in board.GetNetsByName().items():
            s = str(name)
            if s: self.netid[s] = ni.GetNetCode(); self.netname[ni.GetNetCode()] = s
        for h in HALVES:
            edge = (XX < EDGE + h) | (XX > W - EDGE - h) | (YY < EDGE + h) | (YY > L - EDGE - h)
            for l in range(NL): self.OWN[h][l][edge] = -1
        self.novia |= (XX < 0.9) | (XX > W - 0.9) | (YY < 0.9) | (YY > L - 0.9)
        self.PADS = {}
        self.OWNPAD = np.zeros((NY, NX), np.int32)       # net id of the nearest pad within NECK (for neck-down)
        self.OWNPAD_D = np.full((NY, NX), 99.0, np.float32)
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                self._pad(fp, pad)
        self.PADNEAR = np.zeros((NY, NX), bool); self.PADNET = np.zeros((NY, NX), np.int32)
        for nn, plist in self.PADS.items():
            for p in plist:
                if not p["smd"]: continue
                sl = win(p["cx"] - 0.9, p["cy"] - 0.9, p["cx"] + 0.9, p["cy"] + 0.9)
                m = np.hypot(XX[sl] - p["cx"], YY[sl] - p["cy"]) < 0.75
                self.PADNEAR[sl] |= m; self.PADNET[sl][m] = self.netid[nn]
        # escape bands around fine-pitch ICs: costly to travel along, cheap enough to cross once
        self.ESC = np.zeros((NY, NX), np.float32)
        self.ESCV = np.zeros((NY, NX), bool)
        for fp in board.GetFootprints():
            pads = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.GetNumber()]
            if len(pads) < 8: continue
            xs_ = [ToMM(p.GetPosition().x) - OX for p in pads]; ys_ = [ToMM(p.GetPosition().y) - OY for p in pads]
            x0, x1, y0, y1 = min(xs_), max(xs_), min(ys_), max(ys_)
            sl = win(x0 - 3, y0 - 3, x1 + 3, y1 + 3)
            d = rect_dist(x0, y0, x1, y1, sl)
            self.ESC[sl] = np.maximum(self.ESC[sl], np.where((d > 0.3) & (d < 1.6), cfg.get("ESC_COST", 6.0), 0))
            self.ESCV[sl] |= d < 1.4
        # IC body interior (between the pin ring and the exposed pad) belongs to the exposed pad's net only
        for fp in board.GetFootprints():
            pads = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.GetNumber()]
            if len(pads) < 8: continue
            ep = [p for p in pads if ToMM(p.GetSize().x) > 1.0 and ToMM(p.GetSize().y) > 1.0]
            if not ep: continue
            epn = ep[0].GetNetCode()
            ring = [p for p in pads if p not in ep and p.GetNumber() != ep[0].GetNumber()]
            if not ring or not epn: continue
            xs_ = [ToMM(p.GetPosition().x) - OX for p in ring]; ys_ = [ToMM(p.GetPosition().y) - OY for p in ring]
            x0, x1, y0, y1 = min(xs_) + 0.5, max(xs_) - 0.5, min(ys_) + 0.5, max(ys_) - 0.5
            if x1 <= x0 or y1 <= y0: continue
            sl = win(x0, y0, x1, y1)
            for h in HALVES:
                sub = self.OWN[h][0][sl]; sub[sub == 0] = epn
        # hand-drawn local copper zones: their area belongs to the zone net on F.Cu
        self.ZONEMASK = {}
        for zn, poly, *_zp in cfg.get("LOCAL_ZONES", []):
            if zn not in self.netid: continue
            xs_ = [p[0] for p in poly]; ys_ = [p[1] for p in poly]
            sl = win(min(xs_), min(ys_), max(xs_), max(ys_))
            from matplotlib.path import Path as _P
            pts = np.stack([XX[sl].ravel(), YY[sl].ravel()], 1)
            m = _P(poly).contains_points(pts).reshape(XX[sl].shape)
            for h in HALVES:
                sub = self.OWN[h][0][sl]; sub[m & (sub == 0)] = self.netid[zn]
            self.ZONEMASK[zn] = (sl, m)
            # no vias of any net hugging a power pour: their clearance ring would pinch the copper
            sl2 = win(min(xs_) - 1, min(ys_) - 1, max(xs_) + 1, max(ys_) + 1)
            pts2 = np.stack([XX[sl2].ravel(), YY[sl2].ravel()], 1)
            pp = _P(poly)
            near = pp.contains_points(pts2, radius=2 * (VIA_D / 2 + 0.25)) | pp.contains_points(pts2, radius=-2 * (VIA_D / 2 + 0.25))
            self.novia[sl2] |= near.reshape(XX[sl2].shape)
        self.TRACKS, self.VIAS, self.FAIL = [], [], []
        # staggered escape stubs for fine-pitch ICs: every signal pin gets a straight stub outward (short/long alternating)
        skipn = {"GND"} | set(cfg.get("PLANES", ()))
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            if ref not in cfg.get("ESCAPE", {}): continue
            Ls, Ll = cfg["ESCAPE"][ref]
            cx0, cy0 = ToMM(fp.GetPosition().x) - OX, ToMM(fp.GetPosition().y) - OY
            sides = {}
            for p in fp.Pads():
                if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or ToMM(p.GetSize().x) > 1.0 and ToMM(p.GetSize().y) > 1.0: continue
                px, py = ToMM(p.GetPosition().x) - OX, ToMM(p.GetPosition().y) - OY
                dx, dy = px - cx0, py - cy0
                key = ("x", 1 if dx > 0 else -1) if abs(dx) > abs(dy) else ("y", 1 if dy > 0 else -1)
                sides.setdefault(key, []).append((py if key[0] == "x" else px, px, py, p))
            for (ax, sg), lst in sides.items():
                lst.sort()
                for k, (_, px, py, p) in enumerate(lst):
                    nm = p.GetNetname()
                    if not nm or nm in skipn or nm not in self.netid: continue
                    L_ = Ls if k % 2 == 0 else Ll
                    ex, ey = (px + sg * L_, py) if ax == "x" else (px, py + sg * L_)
                    ex, ey = round(ex / G) * G, round(ey / G) * G
                    self.add_track(nm, 0, px, py, ex, ey, 0.15)
        self.HIST = np.zeros((NY, NX), np.float32)

    def claim(self, layer, sl, d, n):
        for h in HALVES:
            sub = self.OWN[h][layer][sl]
            mask = d <= CLR + h + MARGIN
            free = mask & (sub == 0); clash = mask & (sub != 0) & (sub != n)
            sub[free] = n; sub[clash] = -1

    def _pad(self, fp, pad):
        lays = [l for l, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if pad.IsOnLayer(lid)]
        att = pad.GetAttribute()
        cx, cy = ToMM(pad.GetPosition().x) - OX, ToMM(pad.GetPosition().y) - OY
        if att == pcbnew.PAD_ATTRIB_NPTH:
            hr = ToMM(pad.GetDrillSize().x) / 2
            sl = win(cx - hr - 1, cy - hr - 1, cx + hr + 1, cy + hr + 1)
            dd = np.hypot(XX[sl] - cx, YY[sl] - cy)
            for h in HALVES:
                for l in range(NL): self.OWN[h][l][sl][dd <= hr + 0.25 + h + 0.02] = -1
            self.novia[sl][dd <= hr + 0.6] = True
            return
        if not lays: return                               # paste-only apertures
        if att == pcbnew.PAD_ATTRIB_PTH: lays = list(range(NL))
        bb = pad.GetBoundingBox()
        x0, y0 = ToMM(bb.GetX()) - OX, ToMM(bb.GetY()) - OY
        x1, y1 = x0 + ToMM(bb.GetWidth()), y0 + ToMM(bb.GetHeight())
        sl = win(x0 - INFL - 0.6, y0 - INFL - 0.6, x1 + INFL + 0.6, y1 + INFL + 0.6)
        circ = pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE
        d = (np.hypot(XX[sl] - cx, YY[sl] - cy) - (x1 - x0) / 2) if circ else rect_dist(x0, y0, x1, y1, sl)
        n = pad.GetNetCode()
        for l in lays: self.claim(l, sl, d, n if n else -2)
        if att == pcbnew.PAD_ATTRIB_PTH and n and self.netname.get(n) == "GND":
            self.novia[sl][d <= VIA_D / 2 + CLR + 0.02] = True
        else:
            self.novia[sl][d <= VIA_D / 2 + CLR + 0.02] = True
        if n:
            m = (d <= NECK) & (d < self.OWNPAD_D[sl])
            self.OWNPAD[sl][m] = n; self.OWNPAD_D[sl][m] = d[m]
            inside = d <= 0
            jj, ii = np.nonzero(inside)
            cells = [(sl[0].start + j) * NX + (sl[1].start + i) for j, i in zip(jj, ii)]
            self.PADS.setdefault(self.netname[n], []).append(dict(fp=fp.GetReference(), num=pad.GetNumber(), lays=lays,
                cx=cx, cy=cy, cells={l: cells for l in lays}, smd=att == pcbnew.PAD_ATTRIB_SMD,
                small=min(x1 - x0, y1 - y0) < 0.45, mind=min(x1 - x0, y1 - y0)))

    # ---------------------------------------------------------------- copper
    def add_track(self, n, l, ax, ay, bx, by, w):
        if abs(ax - bx) < 1e-6 and abs(ay - by) < 1e-6: return
        self.TRACKS.append((n, l, ax, ay, bx, by, w))
        r = w / 2 + INFL
        sl = win(min(ax, bx) - r - .2, min(ay, by) - r - .2, max(ax, bx) + r + .2, max(ay, by) + r + .2)
        self.claim(l, sl, seg_dist(ax, ay, bx, by, sl) - w / 2, self.netid[n])
    def add_via(self, n, x, y):
        self.VIAS.append((n, x, y))
        r = VIA_D / 2 + INFL
        sl = win(x - r - .2, y - r - .2, x + r + .2, y + r + .2)
        d = np.hypot(XX[sl] - x, YY[sl] - y)
        for l in range(NL): self.claim(l, sl, d - VIA_D / 2, self.netid[n])
        sl2 = win(x - 1.2, y - 1.2, x + 1.2, y + 1.2)
        self.novia[sl2][np.hypot(XX[sl2] - x, YY[sl2] - y) <= VIA_D + 0.2] = True

    # ---------------------------------------------------------------- search
    def window_arrays(self, n, sl):
        nid = self.netid[n]; h = getattr(self, "cls_override", {}).get(n, half(n))
        own = self.OWN[h]; own_n = self.OWN[0.075]
        neck = (self.OWNPAD[sl] == nid)
        legal = []
        al = allowed(n) if n not in ("GND",) + tuple(cfg.get("PLANES", ())) else (0, 1)
        for l in range(NL):
            lg = (own[l][sl] == 0) | (own[l][sl] == nid)
            if h > 0.075:
                lg |= neck & ((own_n[l][sl] == 0) | (own_n[l][sl] == nid))
            if l not in al: lg = np.zeros_like(lg)
            legal.append(lg)
        # via legality: both layers clear for the via radius (narrow class + via radius)
        rad = int(math.ceil((VIA_D / 2 - 0.075) / G - 1e-6))
        ok = ~self.novia[sl]
        for l in range(NL):
            leg = (own_n[l][sl] == 0) | (own_n[l][sl] == nid)
            e = leg.copy()
            for dj in range(-rad, rad + 1):
                for di in range(-rad, rad + 1):
                    if di * di + dj * dj <= rad * rad:
                        e &= np.roll(np.roll(leg, dj, 0), di, 1)
            ok &= e
        ok &= ~(self.ESCV[sl] & (self.OWNPAD[sl] != nid))      # no foreign vias in IC escape bands
        cg = [cfg["cost"](n, l, XX[sl], YY[sl]) + self.HIST[sl] + self.ESC[sl] + 3.0 * (self.PADNEAR[sl] & (self.PADNET[sl] != nid)) for l in range(NL)]
        if n in PAIR_N:                                   # hug the already-routed P conductor at the pair pitch
            pn = PAIR_N[n]
            for l in range(NL):
                segs = [t for t in self.TRACKS if t[0] == pn and int(t[1]) == l]
                if not segs: cg[l] = cg[l] + cfg.get("GUIDE_K", 4.0); continue
                d = np.full(XX[sl].shape, 99.0)
                for t in segs:
                    if max(t[2], t[4]) < XX[sl][0, 0] - 2 or min(t[2], t[4]) > XX[sl][0, -1] + 2: continue
                    if max(t[3], t[5]) < YY[sl][0, 0] - 2 or min(t[3], t[5]) > YY[sl][-1, 0] + 2: continue
                    d = np.minimum(d, seg_dist(t[2], t[3], t[4], t[5], sl))
                cg[l] = cg[l] + cfg.get("GUIDE_K", 4.0) * (np.abs(d - PAIR_PITCH) > 0.06)
        return legal, ok, cg, neck

    def astar(self, n, src, tgt, sl, layers=None, max_expand=2500000):
        """src/tgt: global node ids (layer*N + cell). Search restricted to window sl."""
        j0, i0 = sl[0].start, sl[1].start
        wy, wx = sl[0].stop - j0, sl[1].stop - i0
        WN = wx * wy
        legal, vok, cg, neck = self.window_arrays(n, sl)
        if layers is None: layers = tuple(range(NL))
        LG = [lg.ravel().tolist() for lg in legal]
        VK = vok.ravel().tolist()
        CG = [c.ravel().tolist() for c in cg]
        VIAC = cfg.get("VIA_COST", 25.0)
        def tolocal(g):
            l, k = divmod(g, N); j, i = divmod(k, NX)
            j -= j0; i -= i0
            if 0 <= j < wy and 0 <= i < wx: return l * WN + j * wx + i
            return None
        S = [x for x in (tolocal(g) for g in src) if x is not None]
        T = set(x for x in (tolocal(g) for g in tgt) if x is not None)
        if not S or not T: return None
        tl = [divmod(t % WN, wx) for t in T]
        # heuristic to the target bounding box
        tj0, tj1 = min(t[0] for t in tl), max(t[0] for t in tl); ti0, ti1 = min(t[1] for t in tl), max(t[1] for t in tl)
        S2 = 1.4142
        def hf(k):
            j, i = divmod(k, wx)
            dx = ti0 - i if i < ti0 else (i - ti1 if i > ti1 else 0)
            dy = tj0 - j if j < tj0 else (j - tj1 if j > tj1 else 0)
            return dx + dy + (S2 - 2) * min(dx, dy)
        best = {}; prev = {}; heap = []
        for s in S:
            best[s] = 0.0; prev[s] = -1; heapq.heappush(heap, (hf(s % WN), 0.0, s))
        NB = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, S2), (1, -1, S2), (-1, 1, S2), (-1, -1, S2)]
        expn = 0
        while heap:
            f, g, cur = heapq.heappop(heap)
            if g > best.get(cur, 1e18): continue
            if cur in T:
                path = [cur]
                while prev[path[-1]] != -1: path.append(prev[path[-1]])
                out = []
                for p in path[::-1]:
                    l, k = divmod(p, WN); j, i = divmod(k, wx)
                    out.append(l * N + (j + j0) * NX + (i + i0))
                return out
            expn += 1
            if expn > max_expand: return None
            l, k = divmod(cur, WN); j, i = divmod(k, wx)
            lg = LG[l]; cgl = CG[l]; base = l * WN
            for di, dj, c in NB:
                ii, jj = i + di, j + dj
                if ii < 0 or jj < 0 or ii >= wx or jj >= wy: continue
                kk = jj * wx + ii
                if not lg[kk]: continue
                if di and dj and not (lg[j * wx + ii] and lg[jj * wx + i]): continue
                nxt = base + kk
                ng = g + c * cgl[kk]
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng; prev[nxt] = cur; heapq.heappush(heap, (ng + hf(kk), ng, nxt))
            if VK[k]:
                for l2 in layers:
                    if l2 == l or not LG[l2][k]: continue
                    nxt = l2 * WN + k; ng = g + VIAC
                    if ng < best.get(nxt, 1e18):
                        best[nxt] = ng; prev[nxt] = cur; heapq.heappush(heap, (ng + hf(k), ng, nxt))
        return None

    def emit_path(self, n, path, w):
        nid = self.netid[n]
        pts = []
        for idx in path:
            l, k = divmod(idx, N); j, i = divmod(k, NX)
            hw = half(n)
            ww = w if (w <= 0.15 or self.OWN[hw][min(l, NL - 1)][j, i] in (0, nid)) else 0.15
            pts.append((l, i, j, ww))
        runs, cur = [], [pts[0]]
        for p in pts[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur); self.add_via(n, p[1] * G, p[2] * G); cur = [p]
            else: cur.append(p)
        runs.append(cur)
        for run in runs:
            if len(run) < 2: continue
            l = run[0][0]; a = run[0]; d0 = None
            for k in range(1, len(run)):
                d = (run[k][1] - run[k - 1][1], run[k][2] - run[k - 1][2], run[k][3])
                if d0 is not None and d != d0:
                    b = run[k - 1]; self.add_track(n, l, a[1] * G, a[2] * G, b[1] * G, b[2] * G, min(a[3], d0[2])); a = b
                d0 = d
            b = run[-1]; self.add_track(n, l, a[1] * G, a[2] * G, b[1] * G, b[2] * G, min(a[3], d0[2]) if d0 else a[3])

    def stub(self, n, pad, idx, w):
        l, k = divmod(idx, N); j, i = divmod(k, NX)
        if abs(i * G - pad["cx"]) > 1e-6 or abs(j * G - pad["cy"]) > 1e-6:
            ww = 0.15 if (pad["small"] or w > 0.15) else w
            self.TRACKS.append((n, l, i * G, j * G, pad["cx"], pad["cy"], ww))

    def pad_cells(self, pad):
        out = []
        for l, cells in pad["cells"].items(): out += [l * N + c for c in cells]
        if not out:
            i, j = int(round(pad["cx"] / G)), int(round(pad["cy"] / G))
            out = [l * N + j * NX + i for l in pad["lays"]]
        return out

    def route_net(self, n):
        pads = self.PADS.get(n, [])
        if len(pads) < 2: return
        w = wid(n)
        cx = sum(p["cx"] for p in pads) / len(pads); cy = sum(p["cy"] for p in pads) / len(pads)
        remaining = sorted(pads, key=lambda p: (p["cx"] - cx) ** 2 + (p["cy"] - cy) ** 2)
        first = remaining.pop(0)
        tree = set(self.pad_cells(first)); tree_xy = [(first["cx"], first["cy"])]
        swapped = 0
        tree_pts = [(first["cx"], first["cy"])]        # coarse sample of tree copper for window targeting
        while remaining:
            remaining.sort(key=lambda p: min((p["cx"] - x) ** 2 + (p["cy"] - y) ** 2 for x, y in tree_pts))
            p = remaining.pop(0)
            # overlapping pads of the same pin (SON multi-pad): already joined
            if set(self.pad_cells(p)) & tree:
                tree |= set(self.pad_cells(p)); continue
            tx, ty = min(tree_pts, key=lambda q: (q[0] - p["cx"]) ** 2 + (q[1] - p["cy"]) ** 2)
            path = None
            classes = cfg.get("PAIR_P_CLASSES", [0.45, 0.25, 0.1]) if n in PAIR_P else [None]
            for cls in classes:
                self.cls_override = {n: cls} if cls is not None else {}
                for m in (3.0, 8.0, 20.0):
                    sl = win(min(tx, p["cx"]) - m, min(ty, p["cy"]) - m, max(tx, p["cx"]) + m, max(ty, p["cy"]) + m)
                    path = self.astar(n, self.pad_cells(p), tree, sl)
                    if path: break
                if path: break
            self.cls_override = {}
            if path is None:
                if swapped < 4 and tree == set(self.pad_cells(first)):
                    swapped += 1; remaining.append(first); first = p
                    tree = set(self.pad_cells(p)); tree_pts = [(p["cx"], p["cy"])]; continue
                self.FAIL.append((n, p["fp"], p["num"])); continue
            self.emit_path(n, path, w)
            self.stub(n, p, path[0], w)
            for q in pads:
                if q is not p and path[-1] in set(self.pad_cells(q)): self.stub(n, q, path[-1], w)
            tree |= set(path); tree |= set(self.pad_cells(p))
            for idx in path[::10] + [path[-1]]:
                k = idx % N; j, i = divmod(k, NX); tree_pts.append((i * G, j * G))
            tree_pts.append((p["cx"], p["cy"]))

    def gnd_fanout(self, net="GND"):
        nid = self.netid[net]
        pth = {(q["fp"]) for q in self.PADS[net] if not q["smd"]}
        ep_with_vias = {(q["fp"], q["num"]) for q in self.PADS[net] if not q["smd"]}
        for p in self.PADS[net]:
            if not p["smd"] or (p["fp"], p["num"]) in ep_with_vias: continue
            sl = win(p["cx"] - 3.0, p["cy"] - 3.0, p["cx"] + 3.0, p["cy"] + 3.0)
            legal, vok, cg, neck = self.window_arrays(net, sl)
            j0, i0 = sl[0].start, sl[1].start
            jj, ii = np.nonzero(vok)
            tg = [(j + j0) * NX + (i + i0) for j, i in zip(jj, ii)]
            for q in self.PADS[net]:
                if q["fp"] == p["fp"] and (q["fp"], q["num"]) in ep_with_vias and q is not p:
                    tg += [c for l2, cs in q["cells"].items() if l2 in p["lays"] for c in cs]
            path = self.astar(net, self.pad_cells(p), tg, sl, layers=(0,) if 0 in p["lays"] else (1,), max_expand=80000) if tg else None
            if path is None:
                self.FAIL.append((net, p["fp"], p["num"])); continue
            k = path[-1] % N; j, i = divmod(k, NX); l = path[-1] // N
            if len(path) > 1: self.emit_path(net, path, 0.15)
            self.stub(net, p, path[0], 0.15)
            if vok[j - j0, i - i0] if (0 <= j - j0 < vok.shape[0] and 0 <= i - i0 < vok.shape[1]) else False:
                self.add_via(net, i * G, j * G)

    def preload(self, data, rip=()):
        for t in data["tracks"]:
            if t[0] not in rip: self.add_track(t[0], int(t[1]), *t[2:])
        for v in data["vias"]:
            if v[0] not in rip: self.add_via(*v)

def pair_order(lst):
    """expand differential-pair partners and keep each P directly before its N"""
    out = []
    for n in lst:
        for m in ((n, PAIR_P[n]) if n in PAIR_P else ((PAIR_N[n], n) if n in PAIR_N else (n,))):
            if m not in out: out.append(m)
    return out

def hpwl(R, n):
    ps = R.PADS.get(n, [])
    if not ps: return 0
    xs_ = [p["cx"] for p in ps]; ys_ = [p["cy"] for p in ps]
    return max(xs_) - min(xs_) + max(ys_) - min(ys_)

if __name__ == "__main__":
    PCB = cfg["BOARD"]; OUTJ = cfg["OUTJSON"]
    R0 = Router(pcbnew.LoadBoard(PCB))
    allnets = [n for n in R0.PADS if n != "GND" and n not in cfg.get("PLANES", ()) and len(R0.PADS[n]) > 1]
    first = cfg.get("ORDER_FIRST", [])
    order = [n for n in first if n in allnets] + sorted([n for n in allnets if n not in first], key=lambda n: hpwl(R0, n))
    for pp, nn in PAIRS:
        if pp in order and nn in order:
            order.remove(nn); order.insert(order.index(pp) + 1, nn)
    HIST = np.zeros((NY, NX), np.float32)
    import os
    if cfg.get("RESUME") and os.path.exists(OUTJ + ".hist.npy"):
        HIST = np.load(OUTJ + ".hist.npy"); order = json.load(open(OUTJ + ".order.json"))
        print("resumed history", float(HIST.sum()))
    best = None
    if cfg.get("RESUME") and os.path.exists(OUTJ):
        _b = json.load(open(OUTJ)); best = (_b["tracks"], _b["vias"], [tuple(f) for f in _b["fail"]])
    for attempt in range(cfg.get("ATTEMPTS", 6)):
        t0 = time.time()
        R = Router(pcbnew.LoadBoard(PCB)); R.HIST = HIST
        if not cfg.get("FANOUT_LAST"):
            R.gnd_fanout()
            for pn in cfg.get("PLANES", ()): R.gnd_fanout(pn)
        for n in order: R.route_net(n)
        if cfg.get("FANOUT_LAST"):
            R.gnd_fanout()
            for pn in cfg.get("PLANES", ()): R.gnd_fanout(pn)
        print(f"attempt {attempt}: {len(R.FAIL)} failures, {time.time()-t0:.0f}s  {R.FAIL[:30]}", flush=True)
        if best is None or len(R.FAIL) < len(best[2]): best = (R.TRACKS, R.VIAS, R.FAIL)
        else: print("  (kept previous best with", len(best[2]), "failures)")
        json.dump(dict(tracks=R.TRACKS, vias=R.VIAS, fail=R.FAIL), open(OUTJ + f".last{len(R.FAIL)}.json", "w"), default=float)
        json.dump(dict(tracks=best[0], vias=best[1], fail=best[2]), open(OUTJ, "w"), default=float)
        if not R.FAIL: break
        failed = []
        for f in R.FAIL:
            if f[0] != "GND" and f[0] not in failed: failed.append(f[0])
        order = failed + [n for n in order if n not in failed]
        for f in R.FAIL:
            p = [q for q in R.PADS[f[0]] if q["fp"] == f[1] and q["num"] == f[2]][0]
            sl = win(p["cx"] - 2, p["cy"] - 2, p["cx"] + 2, p["cy"] + 2)
            HIST[sl] += 2.0 * (np.hypot(XX[sl] - p["cx"], YY[sl] - p["cy"]) < 1.5)
        np.save(OUTJ + ".hist.npy", HIST); json.dump(order, open(OUTJ + ".order.json", "w"))
    print("FINAL FAIL", best[2])
