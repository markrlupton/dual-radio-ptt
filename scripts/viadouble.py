# viadouble.py cfg NET[,NET] : give every via of these nets a parallel partner via (joined on F and B) where it fits
import sys, json, math
cfgp = sys.argv[1]; nets = set(sys.argv[2].split(",")); sys.argv = ["x", cfgp]
import router2 as R2, pcbnew
cfg = R2.cfg; r = json.load(open(cfg["OUTJSON"])); b = pcbnew.LoadBoard(cfg["BOARD"])
VD = cfg["VIA"][0]; CL = float(__import__("os").environ.get("CL", "0.17"))
pads = []
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox(); L = set()
        if p.IsOnLayer(pcbnew.F_Cu): L.add(0)
        if p.IsOnLayer(pcbnew.B_Cu): L.add(1)
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH): L = {0, 1, 2}
        pads.append((p.GetNetname(), L, pcbnew.ToMM(bb.GetLeft()) - 100, pcbnew.ToMM(bb.GetTop()) - 50, pcbnew.ToMM(bb.GetRight()) - 100, pcbnew.ToMM(bb.GetBottom()) - 50))
from matplotlib.path import Path as MP
zones = [(z[0], MP(z[1])) for z in cfg.get("LOCAL_ZONES", [])]
def segd(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy; t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)
def seg_clear(n, l, x1, y1, x2, y2, h):
    k = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.05) + 1)
    for i in range(k):
        x = x1 + (x2 - x1) * i / (k - 1); y = y1 + (y2 - y1) * i / (k - 1)
        if not pt_clear(n, {l}, x, y, h): return False
    return True
def pt_clear(n, L, x, y, h):
    if x < 1 or y < 1 or x > 64 or y > 94: return False
    for t in r["tracks"]:
        if t[0] != n and int(t[1]) in L and segd(x, y, *t[2:6]) < h + t[6] / 2 + CL: return False
    for vn, vx, vy in r["vias"]:
        if vn != n and math.hypot(vx - x, vy - y) < h + VD / 2 + CL: return False
    for pn, pl, x0, y0, x1, y1 in pads:
        if pn != n and pl & L and math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) < h + CL: return False
    for zn, zp in zones:
        if zn != n and 0 in L and (zp.contains_point((x, y), radius=h + 0.2) or zp.contains_point((x, y), radius=-(h + 0.2))): return False
    return True
added = 0; skipped = []
for vn, vx, vy in list(r["vias"]):
    if vn not in nets: continue
    if any(n == vn and (x, y) != (vx, vy) and math.hypot(x - vx, y - vy) < 1.0 for n, x, y in r["vias"]): continue   # already has a partner
    done = False
    for d in (0.7, 0.8, 0.95):
        for k in range(16):
            a = k * math.pi / 8; px, py = round(vx + d * math.cos(a), 3), round(vy + d * math.sin(a), 3)
            if not pt_clear(vn, {0, 1, 2}, px, py, VD / 2): continue
            if any(pn == vn and 2 not in pl and math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1)) < VD / 2 + 0.1 for pn, pl, x0, y0, x1, y1 in pads): continue
            if not (seg_clear(vn, 0, vx, vy, px, py, 0.2) and seg_clear(vn, 1, vx, vy, px, py, 0.2)): continue
            r["vias"].append([vn, px, py]); r["tracks"] += [[vn, 0, vx, vy, px, py, 0.4], [vn, 1, vx, vy, px, py, 0.4]]
            added += 1; done = True; break
        if done: break
    if not done: skipped.append((vn, vx, vy))
json.dump(r, open(cfg["OUTJSON"], "w"), default=float)
print("partner vias added", added, "no room", skipped)
