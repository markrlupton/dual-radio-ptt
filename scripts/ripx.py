# rip.py cfg net1,net2,...  : rip these nets and reroute in the given order; keep if failures don't increase
import sys, json
FORCE="force" in sys.argv; cfgp=sys.argv[1]; order=sys.argv[2].split(","); sys.argv=["x",cfgp]
import router2 as R2, pcbnew
order=R2.pair_order(order)
cur=json.load(open(R2.cfg["OUTJSON"]))
R=R2.Router(pcbnew.LoadBoard(R2.cfg["BOARD"])); R.preload(cur, rip=set(order))
for n in order: R.route_net(n)
fail=[tuple(f) for f in cur["fail"] if f[0] not in order]+R.FAIL
print("before",len(cur["fail"]),"after",len(fail),fail)
json.dump(dict(tracks=R.TRACKS,vias=R.VIAS,fail=fail),open("/tmp/ripx_last.json","w"),default=float)
if len(fail)<=len(cur["fail"]) or FORCE:
    json.dump(dict(tracks=R.TRACKS,vias=R.VIAS,fail=fail),open(R2.cfg["OUTJSON"],"w"),default=float); print("saved")
