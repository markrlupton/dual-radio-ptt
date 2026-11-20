# islandvia.py board.kicad_pcb routes.json : add a GND via inside F.Cu GND pour islands that have no via (checks all copper)
import pcbnew, json, math, sys
b = pcbnew.LoadBoard(sys.argv[1]); r = json.load(open(sys.argv[2]))
OX, OY = 100, 50; VR = 0.225; CL = 0.2
def mm(v): return pcbnew.ToMM(v)
segs = []; circ = []; rects = []
for t in b.GetTracks():
    if t.GetNetname() == "GND": continue
    if t.GetClass() == "PCB_VIA": circ.append((mm(t.GetPosition().x) - OX, mm(t.GetPosition().y) - OY, mm(t.GetWidth()) / 2))
    else: segs.append((mm(t.GetStart().x) - OX, mm(t.GetStart().y) - OY, mm(t.GetEnd().x) - OX, mm(t.GetEnd().y) - OY, mm(t.GetWidth()) / 2))
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox(); rects.append((mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY, p.GetNetname()))
for z in b.Zones():
    if z.GetNetname() not in ("GND",) and z.GetLayer() == pcbnew.F_Cu:   # local power pours on F
        fp = z.GetFilledPolysList(pcbnew.F_Cu); bb = fp.BBox()
        rects.append((mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY, z.GetNetname()))
def sd(px, py, a):
    x1, y1, x2, y2, h = a; dx, dy = x2 - x1, y2 - y1; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy) - h
def ok(x, y):
    if any(sd(x, y, s) < VR + CL for s in segs): return False
    if any(math.hypot(x - a, y - c) - h < VR + CL for a, c, h in circ): return False
    for x0, y0, x1, y1, n in rects:
        d = math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))
        if d < VR + (0.05 if n == "GND" else CL): return False
    return True
vias = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
add = 0
for z in b.Zones():
    if z.GetNetname() != "GND" or z.GetLayer() != pcbnew.F_Cu: continue
    fp = z.GetFilledPolysList(pcbnew.F_Cu)
    for i in range(fp.OutlineCount()):
        o = fp.Outline(i)
        if any(o.PointInside(v) for v in vias): continue
        bb = o.BBox(); x0, y0, x1, y1 = mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY
        best = None
        for k in range(int((x1 - x0) / 0.05) + 1):
            for m in range(int((y1 - y0) / 0.05) + 1):
                x, y = x0 + k * 0.05, y0 + m * 0.05
                if not o.PointInside(pcbnew.VECTOR2I(pcbnew.FromMM(x + OX), pcbnew.FromMM(y + OY))): continue
                # keep the via well inside the island
                if not all(o.PointInside(pcbnew.VECTOR2I(pcbnew.FromMM(x + OX + dx), pcbnew.FromMM(y + OY + dy))) for dx, dy in ((0.3, 0), (-0.3, 0), (0, 0.3), (0, -0.3))): continue
                if ok(x, y): best = (x, y); break
            if best: break
        print("island", [round(v, 2) for v in (x0, y0, x1, y1)], "->", best)
        if best: r["vias"].append(["GND", round(best[0], 3), round(best[1], 3)]); add += 1
json.dump(r, open(sys.argv[2], "w"), default=float); print("added", add)
