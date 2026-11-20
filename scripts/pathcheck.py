# pathcheck.py : series vias and narrowest track OUTSIDE pads on the main current paths (from routes.json + board pads)
import json, math, networkx as nx, pcbnew
r=json.load(open("out_revc1/radio_carrier/routes.json")); b=pcbnew.LoadBoard("out_revc1/radio_carrier/carrier_placed.kicad_pcb")
pads={}
for f in b.GetFootprints():
    for q in f.Pads():
        bb=q.GetBoundingBox(); pads.setdefault(q.GetNetname(),[]).append((pcbnew.ToMM(bb.GetLeft())-100,pcbnew.ToMM(bb.GetTop())-50,pcbnew.ToMM(bb.GetRight())-100,pcbnew.ToMM(bb.GetBottom())-50))
def inpad(n,x,y): return any(a-1e-3<=x<=c+1e-3 and b_-1e-3<=y<=d+1e-3 for a,b_,c,d in pads.get(n,[]))
def k(x,y,l): return (round(x,3),round(y,3),l)
def check(net,src,dst):
    G=nx.Graph()
    for t in r["tracks"]:
        if t[0]!=net: continue
        G.add_edge(k(t[2],t[3],int(t[1])),k(t[4],t[5],int(t[1])),w=math.hypot(t[4]-t[2],t[5]-t[3])/t[6]+1e-3,width=t[6],inside=inpad(net,t[2],t[3]) and inpad(net,t[4],t[5]))
    vias=[(v[1],v[2]) for v in r["vias"] if v[0]==net]
    for x,y in vias:
        for l1 in range(3):
            for l2 in range(l1+1,3): G.add_edge(k(x,y,l1),k(x,y,l2),w=0.3,width=9,inside=False)
    nodes=list(G.nodes)
    near=lambda p:min(nodes,key=lambda n:math.hypot(n[0]-p[0],n[1]-p[1])+(0 if n[2]==0 else 9))
    p=nx.shortest_path(G,near(src),near(dst),weight="w")
    vs=[(a[0],a[1]) for a,b in zip(p,p[1:]) if a[:2]==b[:2] and a[2]!=b[2]]
    out=[G[a][b]["width"] for a,b in zip(p,p[1:]) if not (a[:2]==b[:2]) and not G[a][b]["inside"]]
    partner=[sum(1 for x,y in vias if 0<math.hypot(x-vx,y-vy)<2.0) for vx,vy in vs]
    print(f"{net} {src}->{dst}: series vias {len(vs)}, parallel vias per transition {[1+q for q in partner]}, narrowest track outside pads {min(out) if out else '-'} mm")
check("VBUS_IN",(55.48,6.48),(54.75,12.94))
check("VBUS_IN",(58.52,6.48),(54.75,12.94))
