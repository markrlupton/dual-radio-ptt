# viapartner3.py cfg NET x y : extra F->B via near (x,y): on the net's F copper, linked on B to the nearest point of the net's B copper
import sys, json, math
cfgp = sys.argv[1]; net = sys.argv[2]; X, Y = float(sys.argv[3]), float(sys.argv[4]); sys.argv = ["x", cfgp]
exec(open("/home/claude/radio/viadouble.py").read().split("added = 0")[0].replace("nets = set(sys.argv[2].split(\",\")); sys.argv = [\"x\", cfgp]", ""))
def pts_on(layer, near, rad, step=0.05):
    out = []
    for t in r["tracks"]:
        if t[0] != net or int(t[1]) != layer: continue
        L = math.hypot(t[4] - t[2], t[5] - t[3]); k = max(1, int(L / step))
        for i in range(k + 1):
            x = round(t[2] + (t[4] - t[2]) * i / k, 3); y = round(t[3] + (t[5] - t[3]) * i / k, 3)
            if math.hypot(x - near[0], y - near[1]) <= rad: out.append((x, y))
    return out
F = pts_on(0, (X, Y), 3.0); B = pts_on(1, (X, Y), 4.0)
best = None
for fx, fy in F:
    if any(pn == net and 2 not in pl and math.hypot(max(x0 - fx, 0, fx - x1), max(y0 - fy, 0, fy - y1)) < VD / 2 + 0.1 for pn, pl, x0, y0, x1, y1 in pads): continue
    if any(n == net and math.hypot(vx - fx, vy - fy) < 0.6 for n, vx, vy in r["vias"]): continue
    if not pt_clear(net, {0, 1, 2}, fx, fy, VD / 2): continue
    for bx, by in sorted(B, key=lambda p: math.hypot(p[0] - fx, p[1] - fy))[:40]:
        d = math.hypot(bx - fx, by - fy)
        if best and d >= best[0]: break
        if seg_clear(net, 1, fx, fy, bx, by, 0.2): best = (d, fx, fy, bx, by); break
if best:
    d, fx, fy, bx, by = best
    r["vias"].append([net, fx, fy])
    if d > 1e-6: r["tracks"].append([net, 1, fx, fy, bx, by, 0.4])
    json.dump(r, open(cfg["OUTJSON"], "w"), default=float); print("extra via at", fx, fy, "B link %.2f mm" % d)
else: print("none found")
