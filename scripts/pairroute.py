# pairroute.py : coupled single-layer USB pair routing (centerline A* on the pair envelope, then +-PITCH/2 offsets)
import sys, json, heapq, math
cfgp = sys.argv[1]; BOX = [float(v) for v in sys.argv[2].split(",")]; JOBS = json.loads(sys.argv[3]); sys.argv = ["x", cfgp]
import router2 as R2, pcbnew, numpy as np
G, NX, N = R2.G, R2.NX, R2.N
cfg = R2.cfg; HE = 0.4; OFF = cfg["PAIR_PITCH"] / 2; W = cfg["WIDTH"]["USB_A_DP"]
cur = json.load(open(cfg["OUTJSON"]))
x0, y0, x1, y1 = BOX
def inb(x, y): return x0 <= x <= x1 and y0 <= y <= y1
rip = {j["P"] for j in JOBS} | {j["N"] for j in JOBS}
for t in cur["tracks"]:
    if t[0] != "GND" and (inb(t[2], t[3]) or inb(t[4], t[5])): rip.add(t[0])
for v in cur["vias"]:
    if v[0] != "GND" and inb(v[1], v[2]): rip.add(v[0])
rip |= {f[0] for f in cur["fail"] if f[0] != "GND"}
_pairs = {n for pr in cfg["PAIRS"] for n in pr}
rip = {n for n in rip if n not in _pairs or n in {j["P"] for j in JOBS} | {j["N"] for j in JOBS}}
R = R2.Router(pcbnew.LoadBoard(cfg["BOARD"])); R.preload(cur, rip=rip)
def make_R0(PN):                                     # obstacle map without this pair's own pads
    _b = pcbnew.LoadBoard(cfg["BOARD"])
    for f in _b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() in PN: p.SetLayerSet(pcbnew.LSET())
    r0 = R2.Router(_b); r0.preload(dict(tracks=R.TRACKS, vias=R.VIAS)); return r0
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]   # (di, dj)
def centerline(P, Nn, start, d0, goal, wbox, adir=None):
    nP, nN = R.netid[P], R.netid[Nn]
    wi0, wj0 = int(wbox[0] / G), int(wbox[1] / G); wi1, wj1 = int(wbox[2] / G), int(wbox[3] / G)
    own = R0.OWN[HE][0][wj0:wj1, wi0:wi1]
    legal = own == 0
    c = cfg["cost"](P, 0, R2.XX[wj0:wj1, wi0:wi1], R2.YY[wj0:wj1, wi0:wi1])
    si, sj = round(start[0] / G) - wi0, round(start[1] / G) - wj0
    gi, gj = round(goal[0] / G) - wi0, round(goal[1] / G) - wj0
    H, Wd = legal.shape
    if not legal[gj, gi]:
        from scipy import ndimage
        lab, _ = ndimage.label(legal, structure=np.ones((3, 3)))
        comp = lab[sj, si] if legal[sj, si] else lab[sj, si - 2 if d0 == 4 else si + 2]
        jj, ii = np.nonzero(lab == comp); k = np.argmin((jj - gj) ** 2 + (ii - gi) ** 2)
        if (jj[k] - gj) ** 2 + (ii[k] - gi) ** 2 < (3 / G) ** 2: gj, gi = jj[k], ii[k]
    legal[sj, si] = True; legal[gj, gi] = True
    KR = 12                                               # >= 0.6 mm straight between corners (clean offsets)
    best = {}; pq = [(0, 0.0, si, sj, d0, 0, None)]; par = {}
    while pq:
        f, g, i, j, d, r, pr = heapq.heappop(pq)
        k = (i, j, d, r)
        if k in par: continue
        par[k] = pr
        if (i, j) == (gi, gj) and (adir is None or d == adir): break
        for nd in ((d, (d + 1) % 8, (d - 1) % 8) if r >= KR else (d,)):
            di, dj = DIRS[nd]; ni, nj = i + di, j + dj
            if not (0 <= ni < Wd and 0 <= nj < H) or not legal[nj, ni]: continue
            if di and dj and not (legal[j, ni] and legal[nj, i]): continue
            ng = g + (1.4142 if di and dj else 1.0) * c[nj, ni] + (3.0 if nd != d else 0.0)
            nr = min(r + 1, KR) if nd == d else 1
            nk = (ni, nj, nd, nr)
            if nk in par or best.get(nk, 1e18) <= ng: continue
            best[nk] = ng
            h = max(abs(gi - ni), abs(gj - nj)) + 0.4142 * min(abs(gi - ni), abs(gj - nj))
            heapq.heappush(pq, (ng + h, ng, ni, nj, nd, nr, k))
    else:
        np.save("/tmp/legal_%s.npy" % P, legal); print("start", si, sj, legal[sj-3:sj+4, si-12:si+1].astype(int)); return None
    path = []; k = (i, j, d, r)
    while k is not None: path.append(((k[0] + wi0) * G, (k[1] + wj0) * G)); k = par[k]
    path.reverse()
    pts = [path[0]]                                       # keep only corners
    for a, b, cc in zip(path, path[1:], path[2:]):
        if abs((b[0] - a[0]) * (cc[1] - b[1]) - (b[1] - a[1]) * (cc[0] - b[0])) > 1e-9: pts.append(b)
    pts.append(path[-1])
    return pts
def offset(pts, d):
    segs = []
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        segs.append(((a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)))
    out = [segs[0][0]]
    for (a1, a2), (b1, b2) in zip(segs, segs[1:]):
        d1 = (a2[0] - a1[0], a2[1] - a1[1]); d2 = (b2[0] - b1[0], b2[1] - b1[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((b1[0] - a1[0]) * d2[1] - (b1[1] - a1[1]) * d2[0]) / den
        out.append((a1[0] + t * d1[0], a1[1] + t * d1[1]))
    out.append(segs[-1][1])
    return out
def pseudo(n, x, y):
    i, j = round(x / G), round(y / G)
    return dict(fp="PAIR", num="end", lays=[0], cx=x, cy=y, cells={0: [j * NX + i]}, smd=True, small=True)
def padxy(ref, num):
    for n, ps in R.PADS.items():
        for q in ps:
            if q["fp"] == ref and q["num"] == num: return n, q
def esd_fanout(job, P, Nn, eP, eN):
    """flow-through ESD (USBLC6 style, pins 1/6 = P row, 3/4 = N row, 2 GND, 5 VBUS) entered from the left, then down into the connector"""
    e, c = job["esd"], job["conn"]
    _, p1 = padxy(e, "1"); _, p6 = padxy(e, "6"); _, p3 = padxy(e, "3"); _, p4 = padxy(e, "4"); ng, p2 = padxy(e, "2"); nv, p5 = padxy(e, "5")
    _, c7 = padxy(c, "7"); _, c8 = padxy(c, "8")
    xL, xR, yP, yN, yM = p1["cx"], p6["cx"], p1["cy"], p3["cy"], p2["cy"]
    assert abs(p6["cx"] - p4["cx"]) < 1e-3 and xL < xR and yP < yN, "unexpected ESD orientation"
    x7, x8, yc = c7["cx"], c8["cx"], c7["cy"]
    k = 0.5 * (1 - 1 / math.sqrt(2)) / (1 / math.sqrt(2))    # mitre shift for a 0.5 pitch 45 deg corner
    dP = [eP, (xL - 0.86, yP), (xL, yP), (xR, yP), (xR + 1.61, yP), (xR + 1.61, yN + 0.85 + 0.207), (xR + 0.817, yN + 1.85), (x7 + 0.5, yN + 1.85), (x7, yN + 2.35), (x7, yc)]
    dN = [eN, (xL - 0.86, yN), (xL, yN), (xR, yN), (xR + 1.11, yN), (xR + 1.11, yN + 0.85), (xR + 0.61, yN + 1.35), (x8 + 0.5, yN + 1.35), (x8, yN + 1.85), (x8, yc)]
    for n, pts in ((P, dP), (Nn, dN)):
        for u, v in zip(pts, pts[1:]): R.add_track(n, 0, u[0], u[1], v[0], v[1], W)
    gx = (xL + xR) / 2; R.add_track(ng, 0, xL, yM, gx, yM, 0.3)
    if not any(v[0] == ng and abs(v[1] - gx) < 1e-3 and abs(v[2] - yM) < 1e-3 for v in R.VIAS): R.add_via(ng, gx, yM)
    vx = xR + 1.01; R.add_track(nv, 0, xR, yM, vx, yM, 0.3); R.add_via(nv, vx, yM)
    keep = R.PADS[nv]
    vi, vj = round(vx / G), round(yM / G)
    pv = dict(fp="VIA", num="esd", lays=[0, 1, 2], cx=vx, cy=yM, cells={l: [vj * NX + vi] for l in (1, 2)}, smd=False, small=True)
    R.PADS[nv] = [pv] + [q for q in keep if q is not p5]
    R.route_net(nv); R.PADS[nv] = keep
    report.append((P, "ESD flow-through %s -> %s" % (e, c)))
    DONE.add(nv)
DONE = set()
report = []
for job in JOBS:
    P, Nn = job["P"], job["N"]
    R0 = make_R0({P, Nn})
    pP = [q for q in R.PADS[P] if q["fp"] == job["fp"]][0]; pN = [q for q in R.PADS[Nn] if q["fp"] == job["fp"]][0]
    sx = (pP["cx"] + pN["cx"]) / 2; sy = (pP["cy"] + pN["cy"]) / 2
    sx, sy = round(sx / G) * G, round(sy / G) * G
    LEAD = 1.0 if job.get("adir") is not None else 0.0
    ddx, ddy = DIRS[job["adir"]] if LEAD else (0, 0)
    g0 = (job["goal"][0] - ddx * LEAD, job["goal"][1] - ddy * LEAD)
    pts = centerline(P, Nn, (sx, sy), job["dir"], g0, job["win"], job.get("adir"))
    if pts is not None and LEAD: pts[-1] = tuple(job["goal"])
    if pts is None:
        report.append((P, "no centerline")); R.FAIL += [(P, job["fp"], "pair"), (Nn, job["fp"], "pair")]; continue
    a, b = offset(pts, OFF), offset(pts, -OFF)
    # which offset belongs to P: the one starting nearer P's pad
    if math.hypot(a[0][0] - pP["cx"], a[0][1] - pP["cy"]) > math.hypot(b[0][0] - pP["cx"], b[0][1] - pP["cy"]): a, b = b, a
    for n, line in ((P, a), (Nn, b)):
        for u, v in zip(line, line[1:]):
            R.add_track(n, 0, u[0], u[1], v[0], v[1], W)
    L = sum(math.hypot(v[0] - u[0], v[1] - u[1]) for u, v in zip(pts, pts[1:]))
    report.append((P, "centerline %.1f mm, %d corners, ends P %s N %s" % (L, len(pts) - 2, tuple(round(v, 2) for v in a[-1]), tuple(round(v, 2) for v in b[-1]))))
    if "esd" in job:
        esd_fanout(job, P, Nn, a[-1], b[-1]); continue
    # remaining pads join the pair-end, normal router
    for n, line, used in ((P, a, pP), (Nn, b, pN)):
        keep = R.PADS[n]
        R.PADS[n] = [pseudo(n, *line[-1])] + [q for q in keep if q is not used]
        R.route_net(n); R.PADS[n] = keep
order = [n for n in rip if n not in {j["P"] for j in JOBS} | {j["N"] for j in JOBS} | DONE]
order.sort(key=lambda n: R2.hpwl(R, n))
_first = list(dict.fromkeys(n for n in cfg.get("ORDER_FIRST", []) if n in order))
order = _first + [n for n in order if n not in _first]
for n in order: R.route_net(n)
fail = [tuple(f) for f in cur["fail"] if f[0] not in rip] + R.FAIL
for r in report: print(r)
print("ripped", len(rip), "fail", len(fail), fail)
json.dump(dict(tracks=R.TRACKS, vias=R.VIAS, fail=fail), open("/tmp/pair_last.json", "w"), default=float)
if len(fail) <= len(cur["fail"]) or "force" in sys.argv[0]:
    json.dump(dict(tracks=R.TRACKS, vias=R.VIAS, fail=fail), open(cfg["OUTJSON"], "w"), default=float); print("saved")
