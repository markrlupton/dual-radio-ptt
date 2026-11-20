# pourcheck.py : for each power pour, the widest "pipe" that still connects its source and load pads
# (erode the filled copper + same-net F tracks/pads by r; largest r keeping them connected -> min neck width = 2r)
import pcbnew, sys
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union
b = pcbnew.LoadBoard(sys.argv[1] if len(sys.argv) > 1 else "out_revc1/radio_carrier/radio_carrier.kicad_pcb"); OX, OY = 100, 50
mm = pcbnew.ToMM
def copper(net):
    geo = []
    for z in b.Zones():
        if z.GetNetname() == net and z.GetLayer() == pcbnew.F_Cu:
            fp = z.GetFilledPolysList(pcbnew.F_Cu)
            for i in range(fp.OutlineCount()):
                o = fp.Outline(i); geo.append(Polygon([(mm(o.CPoint(j).x) - OX, mm(o.CPoint(j).y) - OY) for j in range(o.PointCount())]).buffer(0))
    for t in b.GetTracks():
        if t.GetNetname() == net and t.GetLayer() == pcbnew.F_Cu and t.GetClass() != "PCB_VIA":
            geo.append(LineString([(mm(t.GetStart().x) - OX, mm(t.GetStart().y) - OY), (mm(t.GetEnd().x) - OX, mm(t.GetEnd().y) - OY)]).buffer(mm(t.GetWidth()) / 2))
    pads = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net and p.IsOnLayer(pcbnew.F_Cu):
                bb = p.GetBoundingBox(); g = box(mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY)
                geo.append(g); pads[f"{f.GetReference()}.{p.GetNumber()}"] = g
    return unary_union(geo), pads
def pipe(net, a, bs):
    cu, pads = copper(net)
    best = 0
    for r in [x * 0.025 for x in range(1, 60)]:
        er = cu.buffer(-r)
        parts = list(er.geoms) if hasattr(er, "geoms") else [er]
        ok = True
        for bname in bs:
            # pads themselves are narrower than the pipe; test connectivity of the regions touching each pad
            pa = [g for g in parts if g.distance(pads[a]) < r + 1e-3]; pb = [g for g in parts if g.distance(pads[bname]) < r + 1e-3]
            if not any(x.equals(y) for x in pa for y in pb): ok = False
        if not ok: break
        best = r
    return 2 * best
for net, a, bs in [("VBAT", "J16.1", ["U10.2"]), ("SYS", "U10.10", ["L1.1", "C104.1", "U11.10"])]:
    print(f"{net}: {a} -> {bs}: narrowest copper on the path about {pipe(net, a, bs):.2f} mm (F.Cu only, no vias)")
