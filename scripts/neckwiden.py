# neckwiden.py cfg NET : widen this net's narrow segments (outside pads) to the widest width that still clears every other net
import sys, json, math
cfgp = sys.argv[1]; net = sys.argv[2]
sys.argv = ["x", cfgp, net]
exec(open("/home/claude/radio/viadouble.py").read().split("added = 0")[0])
want = cfg["WIDTH"][net]; k = 0
def inpad(x, y): return any(pn == net and x0 - 1e-3 <= x <= x1 + 1e-3 and y0 - 1e-3 <= y <= y1 + 1e-3 for pn, pl, x0, y0, x1, y1 in pads)
for t in r["tracks"]:
    if t[0] != net or t[6] >= want or (inpad(t[2], t[3]) and inpad(t[4], t[5])): continue
    for w in [x / 100 for x in range(int(want * 100), int(t[6] * 100), -5)]:
        if seg_clear(net, int(t[1]), t[2], t[3], t[4], t[5], w / 2):
            if w > t[6]: t[6] = w; k += 1
            break
json.dump(r, open(cfg["OUTJSON"], "w"), default=float); print(net, "segments widened", k)
