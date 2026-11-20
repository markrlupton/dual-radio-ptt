# region.py cfg x0,y0,x1,y1 first_nets... : rip every non-GND net with copper in the box, reroute (listed nets first)
import sys, json, math
cfgp, box = sys.argv[1], [float(v) for v in sys.argv[2].split(",")]
first = sys.argv[3].split(",") if len(sys.argv) > 3 else []
sys.argv = ["x", cfgp]
import router2 as R2, pcbnew
cur = json.load(open(R2.cfg["OUTJSON"]))
x0, y0, x1, y1 = box
def inb(x, y): return x0 <= x <= x1 and y0 <= y <= y1
nets = set()
for t in cur["tracks"]:
    if t[0] != "GND" and (inb(t[2], t[3]) or inb(t[4], t[5])): nets.add(t[0])
for v in cur["vias"]:
    if v[0] != "GND" and inb(v[1], v[2]): nets.add(v[0])
nets |= {f[0] for f in cur["fail"] if f[0] != "GND"}
R = R2.Router(pcbnew.LoadBoard(R2.cfg["BOARD"])); R.preload(cur, rip=nets)
order = [n for n in first if n in nets] + sorted([n for n in nets if n not in first], key=lambda n: R2.hpwl(R, n))
for n in order: R.route_net(n)
fail = [tuple(f) for f in cur["fail"] if f[0] not in nets and f[0] != "GND"] + [f for f in cur["fail"] if f[0] == "GND"] + R.FAIL
print("ripped", len(nets), "fail", len(fail), fail)
json.dump(dict(tracks=R.TRACKS, vias=R.VIAS, fail=fail), open("/tmp/region_last.json", "w"), default=float)
old = len(cur["fail"])
if len(fail) < old:
    json.dump(dict(tracks=R.TRACKS, vias=R.VIAS, fail=fail), open(R2.cfg["OUTJSON"], "w"), default=float); print("saved")
