#!/usr/bin/python3
"""routes.json -> tracks/vias on the placed board, GND pours on F/B, stitching vias, zone fill.
usage: finish2.py <cfg.py> <out.kicad_pcb>"""
import pcbnew, math, json, sys, math
from pcbnew import VECTOR2I_MM as P, FromMM, ToMM
cfg = {}; exec(open(sys.argv[1]).read(), cfg)
OUTPCB = sys.argv[2]
W, L, OX, OY = cfg["W"], cfg["L"], cfg["OX"], cfg["OY"]
b = pcbnew.LoadBoard(cfg["BOARD"])
r = json.load(open(cfg["OUTJSON"]))
nets = {str(k): v for k, v in b.GetNetsByName().items()}
_seen = set()
for n, l, ax, ay, bx, by, w in r["tracks"]:
    _k = (n, int(l), round(ax, 3), round(ay, 3), round(bx, 3), round(by, 3), round(w, 3))
    if _k in _seen: continue
    _seen.add(_k)
    if abs(ax - bx) < 1e-6 and abs(ay - by) < 1e-6: continue
    t = pcbnew.PCB_TRACK(b); t.SetStart(P(OX + ax, OY + ay)); t.SetEnd(P(OX + bx, OY + by)); t.SetWidth(FromMM(w))
    t.SetLayer({0: pcbnew.F_Cu, 1: pcbnew.B_Cu, 2: pcbnew.In2_Cu}[int(l)]); t.SetNet(nets[n]); b.Add(t)
# power nets: upgrade each via to the larger size where every other-net copper item still clears
_BIG = cfg.get("BIG_VIA", None); _bign = set(cfg.get("BIG_VIA_NETS", ()))
_pads = []
for _f in b.GetFootprints():
    for _p in _f.Pads():
        _bb = _p.GetBoundingBox(); _pads.append((_p.GetNetname(), ToMM(_bb.GetLeft()) - OX, ToMM(_bb.GetTop()) - OY, ToMM(_bb.GetRight()) - OX, ToMM(_bb.GetBottom()) - OY))
def _segd(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy; t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)
def _fits(n, x, y, size):
    R_ = size[0] / 2 + 0.16
    for t in r["tracks"]:
        if t[0] != n and _segd(x, y, t[2], t[3], t[4], t[5]) < R_ + t[6] / 2: return False
    for vn, vx, vy in r["vias"]:
        if vn != n and math.hypot(vx - x, vy - y) < R_ + cfg.get("VIA", (0.5, 0.25))[0] / 2: return False
    for pn, x0, y0, x1, y1 in _pads:
        if pn != n and math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) < R_: return False
    return True
def _vsize(n, x, y):
    if not _BIG or n not in _bign: return cfg.get("VIA", (0.5, 0.25))
    for size in (_BIG, cfg.get("MID_VIA", (0.5, 0.25))):
        if _fits(n, x, y, size): return size
    return cfg.get("VIA", (0.5, 0.25))
_nbig = 0
for n, x, y in r["vias"]:
    _vs = _vsize(n, x, y); _nbig += _vs != cfg.get("VIA", (0.5, 0.25))
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(OX + x, OY + y)); v.SetDrill(FromMM(_vs[1])); v.SetWidth(FromMM(_vs[0]))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(nets[n]); b.Add(v)
gnd = nets["GND"]
if cfg.get("INNER2"):
    for z in b.Zones():
        if z.GetLayer() == pcbnew.In2_Cu: z.SetNetCode(nets[cfg["INNER2"]].GetNetCode())
for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(lay); z.SetNetCode(gnd.GetNetCode())
    z.SetLocalClearance(FromMM(0.2)); z.SetMinThickness(FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(FromMM(0.2)); z.SetThermalReliefSpokeWidth(FromMM(0.3))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline(); o.NewOutline()
    for x, y in [(0.2, 0.2), (W - 0.2, 0.2), (W - 0.2, L - 0.2), (0.2, L - 0.2)]: o.Append(P(OX + x, OY + y))
    b.Add(z)
for zn, poly, *_zp in cfg.get("LOCAL_ZONES", []):
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNetCode(nets[zn].GetNetCode()); z.SetAssignedPriority(_zp[0] if _zp else 5)
    z.SetLocalClearance(FromMM(0.2)); z.SetMinThickness(FromMM(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    o = z.Outline(); o.NewOutline()
    for x, y in poly: o.Append(P(OX + x, OY + y))
    b.Add(z)
# stitching vias on a 2 mm grid wherever there is room (1.27 mm grid inside the mic area, if defined)
segs, vias, pads = [], [], []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA": vias.append((ToMM(t.GetPosition().x) - OX, ToMM(t.GetPosition().y) - OY))
    else: segs.append((ToMM(t.GetStart().x) - OX, ToMM(t.GetStart().y) - OY, ToMM(t.GetEnd().x) - OX, ToMM(t.GetEnd().y) - OY, ToMM(t.GetWidth()) / 2))
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        pads.append((ToMM(bb.GetX()) - OX, ToMM(bb.GetY()) - OY, ToMM(bb.GetRight()) - OX, ToMM(bb.GetBottom()) - OY))
    for g in fp.GraphicalItems():                       # stay out of courtyards (no vias under parts)
        if g.GetLayer() == pcbnew.F_CrtYd:
            pass
crts = []
for fp in b.GetFootprints():
    bb = fp.GetBoundingBox(False, False)
    crts.append((ToMM(bb.GetX()) - OX, ToMM(bb.GetY()) - OY, ToMM(bb.GetRight()) - OX, ToMM(bb.GetBottom()) - OY))
def segd(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)
import numpy as np
added = []
from matplotlib.path import Path as _MP
_lz = [_MP(z[1]) for z in cfg.get("LOCAL_ZONES", [])]
def free(x, y):
    if any(pz.contains_point((x, y), radius=0.8) or pz.contains_point((x, y), radius=-0.8) for pz in _lz): return False
    if x < 1.2 or x > W - 1.2 or y < 1.2 or y > L - 1.2: return False
    for (x0, y0, x1, y1) in pads:
        if math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) < 0.25 + 0.3: return False
    for (vx, vy) in vias + added:
        if math.hypot(x - vx, y - vy) < 0.5 + 0.3: return False
    for (ax, ay, bx, by, h) in segs:
        if segd(x, y, ax, ay, bx, by) < 0.25 + h + 0.25: return False
    return True
fine = cfg.get("STITCH_FINE", None)
step = 2.0
yy = 1.5
while yy < L - 1.2:
    xx = 1.5
    while xx < W - 1.2:
        if free(xx, yy): added.append((xx, yy))
        xx += step
    yy += step
if fine:
    x0, y0, x1, y1 = fine
    yy = y0
    while yy < y1:
        xx = x0
        while xx < x1:
            if free(xx, yy) and all(math.hypot(xx - a, yy - c) > 1.0 for a, c in added): added.append((xx, yy))
            xx += 1.0
        yy += 1.0
for x, y in added:
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(OX + x, OY + y)); v.SetDrill(FromMM(cfg.get("VIA", (0.5, 0.25))[1])); v.SetWidth(FromMM(cfg.get("VIA", (0.5, 0.25))[0]))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
for txt, x, y, sz in cfg.get("SILK", []):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True); t.SetPosition(P(OX + x, OY + y))
    t.SetTextSize(P(sz, sz)); t.SetTextThickness(FromMM(sz * 0.15)); b.Add(t)
for fp in b.GetFootprints():
    if str(fp.GetFPID().GetLibItemName()).startswith(("PinHeader", "PinSocket", "USB_C")):
        for p in fp.Pads():
            if p.GetNetname() == "GND": p.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    if fp.GetReference() in cfg.get("GND_FULL", ()):
        for p in fp.Pads():
            if p.GetNetname() == "GND": p.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    fp.Reference().SetTextSize(P(0.8, 0.8)); fp.Reference().SetTextThickness(FromMM(0.12))
b.Save(OUTPCB)
import os, json as _j
pro = OUTPCB.replace(".kicad_pcb", ".kicad_pro")
d = _j.load(open(pro)) if os.path.exists(pro) else {}
d.setdefault("meta", {"filename": os.path.basename(pro), "version": 1})
d["board"] = {"design_settings": {"defaults": {}, "rules": {"min_clearance": 0.127, "min_copper_edge_clearance": 0.3,
    "min_through_hole_diameter": 0.2, "min_via_diameter": 0.45, "min_via_annular_width": 0.1, "min_track_width": 0.127,
    "min_text_height": 0.6, "min_text_thickness": 0.08, "min_hole_to_hole": 0.25, "min_hole_clearance": 0.25, "min_silk_clearance": 0.0}}}
d["net_settings"] = {"meta": {"version": 3}, "classes": [{"name": "Default", "clearance": 0.15, "track_width": 0.15,
    "via_diameter": cfg.get("VIA", (0.5, 0.25))[0], "via_drill": cfg.get("VIA", (0.5, 0.25))[1], "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_gap": 0.2,
    "diff_pair_via_gap": 0.25, "diff_pair_width": 0.15, "wire_width": 6, "bus_width": 12, "line_style": 0,
    "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}]}
_j.dump(d, open(pro, "w"), indent=2)
# drop dangling track ends (unused escape stubs, router leftovers), iterate until stable
b2 = pcbnew.LoadBoard(OUTPCB)
for _it in range(10):
    b2.BuildConnectivity(); conn = b2.GetConnectivity(); dead = []
    for t in b2.GetTracks():
        if t.GetClass() == "PCB_TRACK" and conn.TestTrackEndpointDangling(t, False): dead.append(t)
    if not dead: break
    for t in dead: b2.Remove(t)
    print("removed dangling", len(dead))
b2.Save(OUTPCB)
b2 = pcbnew.LoadBoard(OUTPCB); b2.BuildConnectivity()
pcbnew.ZONE_FILLER(b2).Fill(b2.Zones()); b2.Save(OUTPCB)
print("big vias", _nbig); print("tracks", len(r["tracks"]), "vias", len(r["vias"]), "stitch", len(added), "fail", len(r["fail"]))
