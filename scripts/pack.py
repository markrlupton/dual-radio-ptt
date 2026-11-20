import pcbnew, json, sys, itertools
D="/home/claude/radio/out_revc1/radio_carrier"
b=pcbnew.LoadBoard(f"{D}/carrier_placed.kicad_pcb")
pl=json.load(open(f"{D}/placement.json"))
fps={f.GetReference():f for f in b.GetFootprints()}
def bb(f):
    f.BuildCourtyardCaches()
    c=f.GetCourtyard(pcbnew.F_Cu); r=c.BBox() if c.OutlineCount() else f.GetBoundingBox(False,False)
    return [pcbnew.ToMM(v)-o for v,o in zip((r.GetLeft(),r.GetTop(),r.GetRight(),r.GetBottom()),(100,50,100,50))]
def setp(f,x,y,r):
    f.SetPosition(pcbnew.VECTOR2I_MM(100+x,50+y)); f.SetOrientationDegrees(r)
fixed={"J16":(60.9,17.62,90)}
movers=sys.argv[1].split(",")      # parts to re-place
region=[float(v) for v in sys.argv[2].split(",")]  # x0,y0,x1,y1 search window
for r,(x,y,o) in fixed.items(): setp(fps[r],x,y,o); pl[r]=[x,y,o]
B={r:bb(f) for r,f in fps.items() if r not in movers}
def ok(a):
    if a[0]<0.3 or a[1]<0.3 or a[2]>64.7 or a[3]>94.7: return False
    return all(not(a[0]<c[2]-0.02 and c[0]<a[2]-0.02 and a[1]<c[3]-0.02 and c[1]<a[3]-0.02) for c in B.values())
for m in movers:
    f=fps[m]; x0,y0,o0=pl[m]
    best=None
    for o in (o0,(o0+90)%360,(o0+180)%360,(o0+270)%360):
        xs=[region[0]+i*0.1 for i in range(int((region[2]-region[0])/0.1)+1)]
        ys=[region[1]+i*0.1 for i in range(int((region[3]-region[1])/0.1)+1)]
        for x in xs:
            for y in ys:
                d=(x-x0)**2+(y-y0)**2+(0 if o==o0 else 0.5)
                if best and d>=best[0]: continue
                setp(f,x,y,o); a=bb(f)
                if ok(a): best=(d,x,y,o,a)
    assert best, m
    _,x,y,o,a=best; setp(f,x,y,o); B[m]=a; pl[m]=[round(x,2),round(y,2),o]
    print(m,"->",pl[m])
b.Save(f"{D}/carrier_placed.kicad_pcb"); json.dump(pl,open(f"{D}/placement.json","w"))
