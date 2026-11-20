#!/usr/bin/python3
"""Rip-up and reroute on top of routes.json. usage: rr2.py <cfg.py> [iterations]"""
import sys, json, math, time
sys.argv = [sys.argv[0]] + sys.argv[1:]
CFGP = sys.argv[1]; ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
import router2 as R2
from router2 import Router, win, XX, YY, np, cfg as _c
import pcbnew
cfg = {}; exec(open(CFGP).read(), cfg)
R2.cfg.clear(); R2.cfg.update(cfg)
PL = {"GND"} | set(cfg.get("PLANES", ()))
cur = json.load(open(cfg["OUTJSON"]))
cur_fail = [tuple(f) for f in cur["fail"]]
print("start", len(cur_fail), cur_fail, flush=True)

def blockers(R, f, radius=1.5):
    n, fp, num = f
    p = [q for q in R.PADS[n] if q["fp"] == fp and q["num"] == num][0]
    others = [q for q in R.PADS[n] if q is not p]
    o = min(others, key=lambda q: (q["cx"] - p["cx"]) ** 2 + (q["cy"] - p["cy"]) ** 2)
    pts = [(p["cx"], p["cy"], radius), (o["cx"], o["cy"], radius)]
    Ln = max(1, int(math.hypot(o["cx"] - p["cx"], o["cy"] - p["cy"])))
    pts += [(p["cx"] + (o["cx"] - p["cx"]) * t / Ln, p["cy"] + (o["cy"] - p["cy"]) * t / Ln, 1.0) for t in range(1, Ln)]
    cnt = {}
    for (cx, cy, rad) in pts:
        sl = win(cx - rad, cy - rad, cx + rad, cy + rad)
        d = np.hypot(XX[sl] - cx, YY[sl] - cy)
        for l in (0, 1):
            sub = R.OWN[0.075][l][sl]
            for code in np.unique(sub[(d < rad) & (sub > 0)]):
                nm = R.netname.get(int(code))
                if nm and nm != n and nm != "GND":
                    cnt[nm] = cnt.get(nm, 0) + int(((sub == code) & (d < rad)).sum())
    # don't rip nets that own pads there (they are pads, not tracks) -- count only tracks: approximate by keeping all
    return sorted(cnt, key=lambda k: -cnt[k])

tabu = set()
for it in range(ITERS):
    if not cur_fail: break
    f = cur_fail[it % len(cur_fail)]
    R = Router(pcbnew.LoadBoard(cfg["BOARD"])); R.preload(cur)
    bl = [b for b in blockers(R, f) if (f, b) not in tabu]
    if not bl: print(it, f, "no blockers"); continue
    k = 1 + (it // max(1, len(cur_fail))) % 3
    rip_nets = bl[:k]
    for b in rip_nets: tabu.add((f, b))
    rip_nets = [b for b in rip_nets if b not in PL]
    if not rip_nets: continue
    rip_nets = [b for b in R2.pair_order(rip_nets)]
    rip = set(rip_nets) | ({f[0]} if f[0] not in PL else set())
    rip = set(R2.pair_order(sorted(rip)))
    t0 = time.time()
    R = Router(pcbnew.LoadBoard(cfg["BOARD"])); R.preload(cur, rip=rip)
    if f[0] in PL:
        p = [q for q in R.PADS[f[0]] if q["fp"] == f[1] and q["num"] == f[2]][0]
        save = R.PADS[f[0]]; R.PADS[f[0]] = [p] + [q for q in save if not q["smd"]]
        R.gnd_fanout(f[0]); R.PADS[f[0]] = save
    for n in R2.pair_order(([f[0]] if f[0] not in PL else []) + rip_nets): R.route_net(n)
    newfail = [x for x in cur_fail if x[0] not in rip and x != f] + [tuple(x) for x in R.FAIL]
    print(f"{it}: {f} rip {rip_nets} -> {len(newfail)} ({time.time()-t0:.0f}s)", flush=True)
    if len(newfail) < len(cur_fail) or (len(newfail) == len(cur_fail) and set(newfail) != set(cur_fail)):
        cur = dict(tracks=R.TRACKS, vias=R.VIAS, fail=newfail); cur_fail = newfail
        json.dump(cur, open(cfg["OUTJSON"], "w"), default=float)
print("FINAL", len(cur_fail), cur_fail)
