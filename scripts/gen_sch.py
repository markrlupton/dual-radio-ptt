#!/usr/bin/env python3
"""Dual-radio PTT audio board (Teensy 4.0): carrier + front panel schematics, BOMs, expected nets.
Every IC pin map below was checked against the maker's datasheet and/or the KiCad 7 symbol library."""
import uuid, csv, json, os, sys, re
from collections import defaultdict

OUTROOT = sys.argv[1] if len(sys.argv) > 1 else "out"
FPLIB = "radio"  # rev C.2: every footprint lives in the project library <board>/radio.pretty (see mkfplib.py)
G = 2.54
def U(): return str(uuid.uuid4())

# ------------------------------------------------------------------ footprints
FP = {
 "R0603": "Resistor_SMD:R_0603_1608Metric", "C0603": "Capacitor_SMD:C_0603_1608Metric",
 "C0805": "Capacitor_SMD:C_0805_2012Metric", "C1206": "Capacitor_SMD:C_1206_3216Metric",
 "LED0805": "LED_SMD:LED_0805_2012Metric", "SOD123": "Diode_SMD:D_SOD-123", "SOD123F": "Diode_SMD:D_SOD-123F",
 "SOD323": "Diode_SMD:D_SOD-323", "SOT23": "Package_TO_SOT_SMD:SOT-23", "SOT23-5": "Package_TO_SOT_SMD:SOT-23-5",
 "SOT23-6": "Package_TO_SOT_SMD:SOT-23-6",
 "SJ_B": "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm",
 "TP": "TestPoint:TestPoint_Pad_D1.0mm", "MH": "MountingHole:MountingHole_2.7mm_M2.5",
 "SOCK14": "Connector_PinSocket_2.54mm:PinSocket_1x14_P2.54mm_Vertical",
 "HDR1x3": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
 "HDR2x8": "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical",
 "IDC2x8": "Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Vertical",
 "GH10": "Connector_JST:JST_GH_BM10B-GHS-TBT_1x10-1MP_P1.25mm_Vertical",
 "GH6": "Connector_JST:JST_GH_BM06B-GHS-TBT_1x06-1MP_P1.25mm_Vertical",
 "PH2": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
 "USBC": "Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x-0190_6P_TopMnt_Horizontal",
 "SW_SPDT": "Button_Switch_SMD:SW_SPDT_PCM12",
 "XTAL": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
 "L4x4": "Inductor_SMD:L_Bourns-SRN4018",
 "HTQFP64": "Package_QFP:HTQFP-64-1EP_10x10mm_P0.5mm_EP8x8mm_Mask4.4x4.4mm_ThermalVias",
 "SOIC16W": "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", "SOIC8": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
 "VSON10_1622": "Package_SON:Texas_S-PVSON-N10", "SSOP28": "Package_SO:SSOP-28_3.9x9.9mm_P0.635mm",
 "VQFN16": "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
 "WSON10_63060": "Package_SON:Texas_S-PWSON-N10_ThermalVias",
 "WSON12_27762": "Package_SON:WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65_ThermalVias",
 "SOP4": "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", "TSSOP24": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
 "ENC": "Rotary_Encoder:RotaryEncoder_Bourns_Vertical_PEC12R-3x17F-Sxxxx",
 "L4x4XAL": "Inductor_SMD:L_Coilcraft_XAL4020-XXX", "PVSON10TV": "Package_SON:Texas_S-PVSON-N10_ThermalVias",
 "VQFN16TV": "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm_ThermalVias", "X2QFN12": "Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm",
 "PH3": "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical",
 "MF3": "Connector_Molex:Molex_Micro-Fit_3.0_43650-0315_1x03_P3.00mm_Vertical",
 "PUSH12": "Button_Switch_THT:SW_PUSH-12mm", "PUSH6": "Button_Switch_THT:SW_PUSH_6mm",
}
# common JLC/LCSC parts (verify in the JLC BOM tool before ordering)
LCSC_R = {"10k": "C25804", "100k": "C25803", "4.7k": "C23162", "1k": "C21190", "2.2k": "C4190", "33": "C23140",
          "100": "C22775", "47": "C23182", "330": "C23138", "5.1k": "C23186", "0": "C21189", "10": "C22859",
          "1M": "C22935", "200k": "C25811", "2.7k": "C13167"}
LCSC_C = {("100nF", "C0603"): "C14663", ("1uF", "C0603"): "C15849", ("10nF", "C0603"): "C57112",
          ("1nF", "C0603"): "C21122", ("10uF", "C0805"): "C15850", ("22uF", "C0805"): "C45783",
          ("4.7uF", "C0805"): "C1779", ("2.2uF", "C0603"): "C23630", ("10uF", "C0603"): "C19702"}
# named parts: LCSC number looked up by MPN substring (rev C.2; each verified on lcsc.com / jlcpcb.com)
LCSC_PART = {"PCM3168APAPR": "C529289", "INA217AIDWR": "C1849416", "BQ24074RGTR": "C54313", "OPA1678IDR": "C192421",
             "TCA9555PWR": "C465732", "TLV75533PDBVR": "C404027", "TPS2552DBVR": "C46506", "TPS61230DRCR": "C139626",
             "NCP163ASN500T1G": "C603657", "TUSB321RWBR": "C139392", "PESD5V0L1BA": "C85380", "SMF15CA": "C2890424",
             "XAL4020-102MEC": "C4555951", "RT0603BRD0720KL": "C723637", "RT0603BRD074K99L": "C723532",
             "BM10B-GHS-TBT": "C2983879", "BM06B-GHS-TBT": "C189892", "USB4125-GF-A-0190": "C5246813",
             "PCM12SMTR": "C221841", "PEC12R-4217F-S0024": "C49671241"}
# C0G parts: MPN and LCSC chosen together so the dielectric can't be lost in a value-only substitution (rev C.2)
C0G = {("10pF", "C0603"): ("Samsung CL10C100JB8NNNC (C0G 50V 5%)", "C1634"),
       ("18pF", "C0603"): ("Samsung CL10C180JB8NNNC (C0G 50V 5%)", "C1647"),
       ("330pF", "C0603"): ("Samsung CL10C331JB8NNNC (C0G 50V 5%)", "C1664"),
       ("1nF", "C0603"): ("FH 0603CG102J500NT (C0G 50V 5%; alt Samsung CL10C102JB8NNNC C163508)", "C1636"),
       ("2.7nF", "C0603"): ("Walsin 0603N272J500CT (C0G 50V 5%)", "C388043")}

# ------------------------------------------------------------------ schematic writer (one instance per board)
class Sheet:
    def __init__(self, proj, title, paper="A0"):
        self.proj, self.title, self.paper = proj, title, paper
        self.root = U(); self.lib = {}; self.sympins = {}; self.items = []; self.parts = []
        self.pwr_n = 0; self.expect = {}
        self.UP = set(); self.DOWN = {"GND"}
        self.ncpins = set()
        self._base_syms()

    # ---------- s-expr helpers
    @staticmethod
    def fnt(size=1.27, hide=False, justify=None, bold=False):
        j = f" (justify {justify})" if justify else ""; h = " hide" if hide else ""; b = " bold" if bold else ""
        return f"(effects (font (size {size} {size}){b}){j}{h})"
    def prop(self, name, val, x, y, hide=False, justify=None):
        val = str(val).replace('"', "'")
        return f'(property "{name}" "{val}" (at {x:.2f} {y:.2f} 0) {self.fnt(hide=hide, justify=justify)})'
    def pin_s(self, ptype, x, y, ang, length, name, num, hide=False):
        h = " hide" if hide else ""
        return (f'(pin {ptype} line (at {x:.2f} {y:.2f} {ang}) (length {length}){h} '
                f'(name "{name}" {self.fnt()}) (number "{num}" {self.fnt()}))')
    @staticmethod
    def stroke(w=0.254): return f"(stroke (width {w}) (type default))"

    def def_ic(self, name, left, right, width=20.32, refp="U"):
        if name in self.lib: return
        n = max(len(left), len(right)); top = round(((n - 1) * G / 2) / G) * G; hw = width / 2
        pins, pmap = [], {}
        for side, lst in (("L", left), ("R", right)):
            for i, p in enumerate(lst):
                if p is None: continue
                num, pname, ptype = p; y = top - i * G
                x = -(hw + G) if side == "L" else (hw + G)
                pins.append(self.pin_s(ptype, x, y, 0 if side == "L" else 180, G, pname, num)); pmap[num] = (x, y, side)
                if ptype == "no_connect": self.ncpins.add((name, num))
        y1, y2 = top + G, top - n * G
        body = f'(rectangle (start {-hw:.2f} {y1:.2f}) (end {hw:.2f} {y2:.2f}) {self.stroke()} (fill (type background)))'
        self.lib[name] = (f'(symbol "lib:{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n'
            f'  {self.prop("Reference", refp, 0, y1 + 1.27)}\n  {self.prop("Value", name, 0, y2 - 1.27)}\n'
            f'  {self.prop("Footprint", "", 0, 0, True)}\n  {self.prop("Datasheet", "", 0, 0, True)}\n'
            f'  (symbol "{name}_0_1" {body})\n  (symbol "{name}_1_1" {" ".join(pins)}))')
        self.sympins[name] = pmap

    def def_two(self, name, refp, graphics, pinlen, names=("~", "~")):
        pins = [self.pin_s("passive", 0, 3.81, 270, pinlen, names[0], "1"), self.pin_s("passive", 0, -3.81, 90, pinlen, names[1], "2")]
        self.lib[name] = (f'(symbol "lib:{name}" (pin_numbers hide) (pin_names (offset 0) hide) (in_bom yes) (on_board yes)\n'
            f'  {self.prop("Reference", refp, 2.54, 1.27, justify="left")}\n  {self.prop("Value", name, 2.54, -1.27, justify="left")}\n'
            f'  {self.prop("Footprint", "", 0, 0, True)}\n  {self.prop("Datasheet", "", 0, 0, True)}\n'
            f'  (symbol "{name}_0_1" {graphics})\n  (symbol "{name}_1_1" {" ".join(pins)}))')
        self.sympins[name] = {"1": (0, 3.81, "T"), "2": (0, -3.81, "B")}

    def def_power(self, name, style):
        st = self.stroke()
        if style == "up":
            g = f'(polyline (pts (xy 0 0) (xy 0 1.27)) {st} (fill (type none))) (polyline (pts (xy -1.27 1.27) (xy 1.27 1.27)) {st} (fill (type none)))'; vy = 2.54
        elif style == "flag":
            g = f'(polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)) (stroke (width 0) (type default)) (fill (type none)))'; vy = 3.175
        else:
            g = f'(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) {st} (fill (type none)))'; vy = -3.81
        flag = style == "flag"; sym = "PWR_FLAG" if flag else name
        self.lib[sym] = (f'(symbol "lib:{sym}" (power) (pin_names (offset 0)) (in_bom yes) (on_board yes)\n'
            f'  {self.prop("Reference", "#FLG" if flag else "#PWR", 0, -5.08, True)}\n  {self.prop("Value", sym, 0, vy)}\n'
            f'  {self.prop("Footprint", "", 0, 0, True)}\n  {self.prop("Datasheet", "", 0, 0, True)}\n'
            f'  (symbol "{sym}_0_1" {g})\n'
            f'  (symbol "{sym}_1_1" {self.pin_s("power_out" if flag else "power_in", 0, 0, 270 if style == "down" else 90, 0, sym, "1", hide=True)}))')

    def _base_syms(self):
        st = self.stroke()
        self.def_two("R", "R", f'(rectangle (start -1.016 2.54) (end 1.016 -2.54) {st} (fill (type none)))', 1.27)
        self.def_two("C", "C", '(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none))) '
                               '(polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))', 3.048)
        self.def_two("L", "L", f'(rectangle (start -0.762 2.54) (end 0.762 -2.54) {st} (fill (type outline)))', 1.27)
        # diode: pin 1 = cathode (top), pin 2 = anode (bottom); triangle points up
        self.def_two("D", "D", f'(polyline (pts (xy -1.27 -1.016) (xy 1.27 -1.016) (xy 0 1.016) (xy -1.27 -1.016)) {st} (fill (type none))) '
                               f'(polyline (pts (xy -1.27 1.016) (xy 1.27 1.016)) {st} (fill (type none)))', 2.794, ("K", "A"))
        self.def_two("LED", "D", f'(polyline (pts (xy -1.27 -1.016) (xy 1.27 -1.016) (xy 0 1.016) (xy -1.27 -1.016)) {st} (fill (type outline))) '
                                 f'(polyline (pts (xy -1.27 1.016) (xy 1.27 1.016)) {st} (fill (type none)))', 2.794, ("K", "A"))
        self.def_two("TVS_BI", "D", f'(polyline (pts (xy -1.27 1.016) (xy 1.27 1.016) (xy 0 0) (xy -1.27 1.016)) {st} (fill (type none))) '
                                    f'(polyline (pts (xy -1.27 -1.016) (xy 1.27 -1.016) (xy 0 0) (xy -1.27 -1.016)) {st} (fill (type none)))', 2.794)
        self.def_two("SJ", "JP", f'(rectangle (start -1.27 2.54) (end 1.27 0.381) {st} (fill (type outline))) (rectangle (start -1.27 -0.381) (end 1.27 -2.54) {st} (fill (type outline)))', 1.27)
        self.def_two("SW", "SW", f'(polyline (pts (xy 0 -1.5) (xy 1.5 1.5)) {st} (fill (type none)))', 2.54)
        self.def_two("TP", "TP", f'(circle (center 0 0) (radius 0.8) {st} (fill (type none)))', 3.0)
        self.def_power("GND", "down"); self.def_power("PWR_FLAG", "flag")

    def rail(self, name):
        if name not in self.lib and name not in self.DOWN:
            self.def_power(name, "up"); self.UP.add(name)

    # ---------- parts
    def add(self, ref, sym, value, fp, nets, mpn="", lcsc="", note="", dnp=False):
        if not lcsc:
            lcsc = next((v for k, v in LCSC_PART.items() if k in (mpn or "") or k == value), "")
        self.parts.append(dict(ref=ref, sym=sym, value=value, fp=FP.get(fp, fp), nets=nets, mpn=mpn, lcsc=lcsc, note=note, dnp=dnp))
        for p, n in nets.items():
            if n is not None: self.expect[(ref, p)] = n

    def R(self, ref, val, n1, n2, note="", tol="1%", fp="R0603", dnp=False, mpn=None, lcsc=None):
        self.add(ref, "R", val, fp, {"1": n1, "2": n2}, mpn or f"0603 {tol} resistor", lcsc or (LCSC_R.get(val, "") if tol == "1%" else ""), note, dnp)
    def C(self, ref, val, n1, n2, note="", fp="C0603", diel="X7R", dnp=False):
        v = {"C0603": "16V", "C0805": "16V", "C1206": "25V"}[fp]
        if diel == "C0G" and (val, fp) in C0G:
            mpn, lc = C0G[(val, fp)]
            self.add(ref, "C", val, fp, {"1": n1, "2": n2}, mpn, lc, note, dnp); return
        assert diel != "C0G", f"{ref}: no C0G part selected for {val} {fp}"
        self.add(ref, "C", val, fp, {"1": n1, "2": n2}, f"{fp[1:]} {diel} {v}", LCSC_C.get((val, fp), ""), note, dnp)

    # ---------- layout + emit
    def layout(self, blocks):
        """blocks: list of (title, x, y, [refs], cols). ICs/connectors first in the list get a column of their own."""
        self.titles = []
        byref = {p["ref"]: p for p in self.parts}
        placed = set()
        for title, bx, by, refs, cols in blocks:
            self.titles.append((title, bx, by - 10))
            x, y = bx, by + 6; colw = 0; rowh = 0; ci = 0
            big = [r for r in refs if byref[r]["sym"] not in ("R", "C", "L", "D", "LED", "TVS_BI", "SJ", "SW", "TP")]
            small = [r for r in refs if r not in big]
            cx = bx
            for r in big:
                p = byref[r]; pm = self.sympins[p["sym"]]
                ys = [v[1] for v in pm.values()] or [0]; xs = [v[0] for v in pm.values()] or [0]
                h = (max(ys) - min(ys)) + 12; w = (max(xs) - min(xs)) + 30
                p["x"] = cx + w / 2 - 0; p["y"] = by + max(ys) + 8
                p["x"] = round(p["x"] / G) * G; p["y"] = round(p["y"] / G) * G
                cx += w + 10; placed.add(r)
            sx = cx + 10
            for i, r in enumerate(small):
                p = byref[r]; c, row = i % cols, i // cols
                p["x"] = round((sx + c * 17.78) / G) * G; p["y"] = round((by + 12 + row * 30.48) / G) * G
                placed.add(r)
        mx = max(p["x"] for p in self.parts); my = max(p["y"] for p in self.parts); print(self.proj, "extent", mx, my)
        missing = [p["ref"] for p in self.parts if p["ref"] not in placed]
        assert not missing, f"unplaced: {missing}"

    def label(self, net, x, y, ang):
        just = {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[ang]
        self.items.append(f'(label "{net}" (at {x:.2f} {y:.2f} {ang}) (fields_autoplaced) {self.fnt(justify=just)} (uuid {U()}))')
    def wire(self, x1, y1, x2, y2):
        self.items.append(f'(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid {U()}))')
    def power(self, net, x, y):
        self.pwr_n += 1; ref = f"#PWR{self.pwr_n:04d}"; vy = y - 2.54 if net in self.UP else y + 3.81
        self.items.append(f'(symbol (lib_id "lib:{net}") (at {x:.2f} {y:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {U()})\n'
            f'  {self.prop("Reference", ref, x, y + 5.08, True)}\n  {self.prop("Value", net, x, vy)}\n'
            f'  {self.prop("Footprint", "", x, y, True)}\n  {self.prop("Datasheet", "", x, y, True)}\n  (pin "1" (uuid {U()}))\n'
            f'  (instances (project "{self.proj}" (path "/{self.root}" (reference "{ref}") (unit 1)))))')
    def flag(self, x, y):
        self.pwr_n += 1; ref = f"#FLG{self.pwr_n:04d}"
        self.items.append(f'(symbol (lib_id "lib:PWR_FLAG") (at {x:.2f} {y:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {U()})\n'
            f'  {self.prop("Reference", ref, x, y + 2.54, True)}\n  {self.prop("Value", "PWR_FLAG", x, y - 3.81)}\n'
            f'  {self.prop("Footprint", "", x, y, True)}\n  {self.prop("Datasheet", "", x, y, True)}\n  (pin "1" (uuid {U()}))\n'
            f'  (instances (project "{self.proj}" (path "/{self.root}" (reference "{ref}") (unit 1)))))')
    def noconn(self, x, y): self.items.append(f'(no_connect (at {x:.2f} {y:.2f}) (uuid {U()}))')

    def emit(self, outdir, flags=(), texts=()):
        os.makedirs(outdir, exist_ok=True)
        allnets = set(n for p in self.parts for n in p["nets"].values() if n)
        for n in allnets:
            if n.startswith("+") or n.startswith("-") or n in ("VBAT", "SYS", "VBUS_IN"): self.rail(n)
        POWER = self.UP | self.DOWN
        for p in self.parts:
            sym, X, Y = p["sym"], p["x"], p["y"]; pm = self.sympins[sym]
            two = len(pm) == 2 and set(pm) == {"1", "2"} and pm["1"][2] == "T"
            if two: rp, vp = (X + 2.54, Y - 1.27), (X + 2.54, Y + 1.27)
            else:
                ys = [v[1] for v in pm.values()] or [0]
                rp, vp = (X, Y - (max(ys) + 2 * G) - 1.27), (X, Y - (min(ys) - 2 * G) + 1.27)
            props = [self.prop("Reference", p["ref"], *rp, justify="left" if two else None),
                     self.prop("Value", p["value"], *vp, justify="left" if two else None),
                     self.prop("Footprint", (FPLIB + ":" + p["fp"].split(":")[1]) if (FPLIB and p["fp"]) else p["fp"], X, Y, True), self.prop("Datasheet", "", X, Y, True),
                     self.prop("MPN", p["mpn"], X, Y, True), self.prop("LCSC", p["lcsc"], X, Y, True)]
            pins = " ".join(f'(pin "{n}" (uuid {U()}))' for n in pm)
            dnp = "yes" if p["dnp"] else "no"
            self.items.append(f'(symbol (lib_id "lib:{sym}") (at {X:.2f} {Y:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp {dnp}) (uuid {U()})\n  '
                              + "\n  ".join(props) + f"\n  {pins}\n"
                              f'  (instances (project "{self.proj}" (path "/{self.root}" (reference "{p["ref"]}") (unit 1)))))')
            side_pw = {}
            for num, (px, py, side) in pm.items():
                sx, sy = X + px, Y - py; net = p["nets"].get(num)
                if net is None:
                    if (sym, num) not in self.ncpins: self.noconn(sx, sy)   # a no_connect-type pin needs no flag (KiCad calls one there dangling)
                    continue
                if net in POWER:
                    if side == "T":
                        if net in self.UP: self.power(net, sx, sy)
                        else: self.wire(sx, sy, sx, sy - 2.54); self.power(net, sx, sy - 2.54)
                    elif side == "B":
                        if net in self.DOWN: self.power(net, sx, sy)
                        else: self.wire(sx, sy, sx, sy + 2.54); self.power(net, sx, sy + 2.54)
                    else: side_pw.setdefault((side, net), []).append((sx, sy))
                else:
                    self.label(net, sx, sy, {"L": 180, "R": 0, "T": 90, "B": 270}[side])
            for (side, net), pts in side_pw.items():
                dx = -5.08 if side == "L" else 5.08
                pts.sort(key=lambda q: q[1]); runs, cur = [], [pts[0]]
                for q in pts[1:]:
                    if abs(q[1] - cur[-1][1] - G) < 0.01: cur.append(q)
                    else: runs.append(cur); cur = [q]
                runs.append(cur)
                for run in runs:
                    bx = run[0][0] + dx
                    for (qx, qy) in run: self.wire(qx, qy, bx, qy)
                    if len(run) > 1:
                        for a, b in zip(run, run[1:]): self.wire(bx, a[1], bx, b[1])
                        for (qx, qy) in run[1:-1]: self.items.append(f'(junction (at {bx:.2f} {qy:.2f}) (diameter 0) (color 0 0 0 0) (uuid {U()}))')
                    self.power(net, bx, run[0][1] if net in self.UP else run[-1][1])
        fx = 30.48
        for net in flags:
            self.flag(fx, 20.32); self.wire(fx, 20.32, fx, 25.4 if net in self.UP else 22.86); self.power(net, fx, 25.4 if net in self.UP else 22.86); fx += 12.7
        for (t, x, y) in getattr(self, "titles", []):
            self.items.append(f'(text "{t}" (at {x:.2f} {y:.2f} 0) {self.fnt(2.5, justify="left bottom", bold=True)} (uuid {U()}))')
        for (t, x, y, s) in texts:
            self.items.append(f'(text "{t}" (at {x:.2f} {y:.2f} 0) {self.fnt(s, justify="left bottom")} (uuid {U()}))')
        sch = (f'(kicad_sch (version 20230121) (generator eeschema)\n(uuid {self.root})\n(paper "{self.paper}")\n'
               f'(title_block (title "{self.title}") (date "2026-11-20") (rev "C.1"))\n'
               '(lib_symbols\n' + "\n".join(self.lib.values()) + '\n)\n' + "\n".join(self.items) +
               '\n(sheet_instances (path "/" (page "1")))\n)\n')
        open(f"{outdir}/{self.proj}.kicad_sch", "w").write(sch)
        # project symbol library "lib" (same definitions the schematic embeds) so ERC finds every symbol's library
        syms = [re.sub(r'^\(symbol "lib:([^"]+)"', r'(symbol "\1"', v, count=1) for v in self.lib.values()]
        open(f"{outdir}/lib.kicad_sym", "w").write('(kicad_symbol_lib (version 20220914) (generator gen_sch)\n' + "\n".join(syms) + '\n)\n')
        open(f"{outdir}/sym-lib-table", "w").write('(sym_lib_table\n  (lib (name "lib")(type "KiCad")(uri "${KIPRJMOD}/lib.kicad_sym")(options "")(descr "radio board symbols"))\n)\n')
        open(f"{outdir}/{self.proj}.kicad_pro", "w").write(json.dumps({"meta": {"filename": f"{self.proj}.kicad_pro", "version": 1}}, indent=2))
        json.dump({f"{r}.{p}": n for (r, p), n in self.expect.items()}, open(f"{outdir}/expected_nets.json", "w"), indent=1)
        self.bom(outdir)

    def bom(self, outdir):
        grp = defaultdict(list)
        for p in self.parts:
            if p["sym"] in ("TP",) or p["fp"] == FP["MH"] or p["sym"] == "SJ": continue
            grp[(p["value"], p["fp"], p["mpn"], p["lcsc"], p["dnp"])].append(p)
        def rk(r):
            m = re.match(r"([A-Z]+)(\d+)", r); return (m.group(1), int(m.group(2))) if m else (r, 0)
        rows = sorted(grp.items(), key=lambda kv: rk(sorted([q["ref"] for q in kv[1]], key=rk)[0]))
        def hand(fp): return fp.split(":")[0] in ("Connector_PinSocket_2.54mm", "Connector_PinHeader_2.54mm", "Connector_PinHeader_1.27mm", "Connector_JST",
                                                  "Connector_USB", "Button_Switch_THT", "Rotary_Encoder", "Button_Switch_SMD", "Connector_Molex")
        def comment(val, mpn):
            generic = (not mpn) or mpn[:1].isdigit() or mpn.startswith(("not fitted",)) or " X7R " in mpn or " C0G " in mpn
            if generic: return val
            toks = [t for t in mpn.split(" (")[0].split() if t not in ("TI", "Yageo", "onsemi", "ST", "Nexperia", "Bourns", "Coilcraft", "JST", "GCT", "C&K", "Panasonic", "Terminus", "Vishay", "Molex", "FH", "Viking", "RALEC", "LIZ", "YXC", "Samsung", "Walsin", "NationStar")]
            return toks[0] if toks else val
        with open(f"{outdir}/{self.proj}_BOM_JLC.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for (val, fp, mpn, lcsc, dnp), ps in rows:
                if dnp: continue
                w.writerow([comment(val, mpn), ",".join(sorted([q["ref"] for q in ps], key=rk)), fp.split(":")[1], lcsc])
        with open(f"{outdir}/{self.proj}_BOM_full.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["Qty", "Designator", "Value", "Description / MPN", "Footprint", "LCSC", "Fitted", "Assembly", "Note"])
            for (val, fp, mpn, lcsc, dnp), ps in rows:
                notes = "; ".join(sorted({q["note"] for q in ps if q["note"]}))
                w.writerow([len(ps), ",".join(sorted([q["ref"] for q in ps], key=rk)), val, mpn, fp.split(":")[1], lcsc or "choose",
                            "DNP" if dnp else "yes", "hand-solder" if hand(fp) else "SMT", notes])

pi, po, bi, pa, pwi, pwo, nc, oc = "input", "output", "bidirectional", "passive", "power_in", "power_out", "no_connect", "open_collector"

# =================================================================== CARRIER
S = Sheet("radio_carrier", "Dual-Radio PTT Audio Carrier (Teensy 4.0) rev C - PCM3168A / INA217 / OPA1622 / FE1.1s", "A0")

# ---- symbols
TL = ["GND", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
TR = ["VIN", "GND", "3V3", "23", "22", "21", "20", "19", "18", "17", "16", "15", "14", "13"]
S.def_ic("Teensy40_L", [], [(str(i + 1), n, pa) for i, n in enumerate(TL)], 12.7, "J")
S.def_ic("Teensy40_R", [], [(str(i + 1), n, pa) for i, n in enumerate(TR)], 12.7, "J")
S.def_ic("PCM3168A", width=33.02, left=[
    ("3", "VCCAD2", pwi), ("49", "VCCAD1", pwi), ("14", "VCCDA1", pwi), ("34", "VCCDA2", pwi), ("46", "VDD1", pwi), ("12", "VDD2", pwi), None,
    ("41", "SCKI", pi), ("7", "BCKAD", bi), ("36", "BCKDA", bi), ("6", "LRCKAD", bi), ("35", "LRCKDA", bi),
    ("37", "DIN1", pi), ("38", "DIN2", pi), ("39", "DIN3", pi), ("40", "DIN4", pi),
    ("8", "DOUT1", po), ("9", "DOUT2", po), ("10", "DOUT3", po), None,
    ("42", "MC/SCL/FMT", pi), ("43", "MDI/SDA/DEMP", bi), ("44", "MDO/ADR1/MD1", pi), ("45", "MS/ADR0/MD0", pi),
    ("48", "MODE", pi), ("4", "~{RST}", pi), ("5", "OVF", po), ("13", "ZERO", po), None,
    ("2", "AGNDAD2", pwi), ("50", "AGNDAD1", pwi), ("16", "AGNDDA1", pwi), ("33", "AGNDDA2", pwi), ("11", "DGND2", pwi), ("47", "DGND1", pwi), ("65", "EP", pwi)],
  right=[("52", "VIN1+", pi), ("51", "VIN1-", pi), ("54", "VIN2+", pi), ("53", "VIN2-", pi), ("56", "VIN3+", pi), ("55", "VIN3-", pi),
    ("58", "VIN4+", pi), ("57", "VIN4-", pi), ("62", "VIN5+", pi), ("61", "VIN5-", pi), ("64", "VIN6+", pi), ("63", "VIN6-", pi), None,
    ("1", "VCOMAD", pa), ("15", "VCOMDA", pa), ("59", "VREFAD1", pa), ("60", "VREFAD2", pa), None,
    ("31", "VOUT1+", po), ("32", "VOUT1-", po), ("29", "VOUT2+", po), ("30", "VOUT2-", po), ("27", "VOUT3+", po), ("28", "VOUT3-", po),
    ("25", "VOUT4+", po), ("26", "VOUT4-", po), ("23", "VOUT5+", po), ("24", "VOUT5-", po), ("21", "VOUT6+", po), ("22", "VOUT6-", po),
    ("19", "VOUT7+", po), ("20", "VOUT7-", po), ("17", "VOUT8+", po), ("18", "VOUT8-", po)])
S.def_ic("INA217_SOIC16", width=17.78, left=[("5", "VIN+", pi), ("4", "VIN-", pi), None, ("2", "RG1", pa), ("15", "RG2", pa), None,
    ("1", "NC", nc), ("3", "NC", nc), ("6", "NC", nc), ("8", "NC", nc)],
  right=[("13", "V+", pwi), ("7", "V-", pwi), None, ("11", "VOUT", po), ("10", "REF", pi), None, ("9", "NC", nc), ("12", "NC", nc), ("14", "NC", nc), ("16", "NC", nc)])
S.def_ic("OPA1622", width=15.24, left=[("1", "+INA", pi), ("10", "-INA", pi), None, ("5", "+INB", pi), ("6", "-INB", pi), None, ("8", "EN", pi)],
  right=[("2", "V+", pwi), ("9", "OUTA", po), ("7", "OUTB", po), ("3", "GND", pwi), None, ("4", "V-", pwi), ("11", "EP(V-)", pwi)])
S.def_ic("OPA1678", width=15.24, left=[("3", "+INA", pi), ("2", "-INA", pi), None, ("5", "+INB", pi), ("6", "-INB", pi)],
  right=[("8", "V+", pwi), ("1", "OUTA", po), ("7", "OUTB", po), None, ("4", "V-", pwi)])
S.def_ic("AQY212GS", width=12.7, refp="K", left=[("1", "LED A", pa), ("2", "LED K", pa)], right=[("4", "D", pa), ("3", "D", pa)])
S.def_ic("2N7002", width=7.62, refp="Q", left=[("1", "G", pi)], right=[("3", "D", pa), ("2", "S", pa)])
S.def_ic("BAV99", width=7.62, refp="D", left=[("3", "K1/A2", pa)], right=[("2", "K2", pa), ("1", "A1", pa)])
S.def_ic("FE1.1s", width=22.86, left=[("20", "VDD5", pwi), ("21", "VD33_O", pwo), ("13", "VD33", pwi), ("12", "VD18_O", pwo), ("28", "VD18", pwi), None,
    ("3", "XIN", pi), ("2", "XOUT", po), ("14", "REXT", pa), ("17", "~{XRSTJ}", pi), ("18", "VBUSM", pi), ("19", "BUSJ", pi), None,
    ("22", "DRV", bi), ("23", "LED1/EESCL", bi), ("24", "LED2", bi), ("25", "PWRJ", po), ("26", "OVCJ", pi), ("27", "TESTJ/EESDA", bi), None, ("1", "VSS", pwi)],
  right=[("16", "DPU", bi), ("15", "DMU", bi), None, ("11", "DP1", bi), ("10", "DM1", bi), ("9", "DP2", bi), ("8", "DM2", bi),
    ("7", "DP3", bi), ("6", "DM3", bi), ("5", "DP4", bi), ("4", "DM4", bi)])
S.def_ic("TPS2552", width=12.7, left=[("1", "IN", pwi), ("3", "~{EN}", pi), ("5", "ILIM", pa)], right=[("6", "OUT", pwo), ("4", "~{FAULT}", oc), ("2", "GND", pwi)])
S.def_ic("TPS61230DRC", width=15.24, left=[("10", "VIN", pwi), ("9", "EN", pi), ("8", "HYS", pa), ("6", "SS", pa), ("1", "SW", pa), ("2", "SW", pa)],
  right=[("3", "VOUT", pwo), ("4", "VOUT", pa), ("7", "FB", pi), ("5", "PG", oc), ("11", "GND", pwi)])
S.def_ic("TUSB321", width=17.78, left=[("12", "VDD", pwi), ("5", "VBUS_DET", pi), ("1", "CC1", bi), ("2", "CC2", bi), ("4", "PORT", pi), ("3", "CURRENT_MODE", pi)],
  right=[("7", "OUT1", oc), ("8", "OUT2", oc), ("9", "ID", oc), ("6", "~{VCONN_FAULT}", oc), ("11", "DIR", oc), ("10", "GND", pwi)])
S.def_ic("Conn_3x", width=10.16, refp="J", left=[("1", "1", pa), ("2", "2", pa), ("3", "3", pa)], right=[])
S.def_ic("USBLC6-2SC6", width=12.7, refp="U", left=[("1", "IO1", pa), ("6", "IO1", pa), ("3", "IO2", pa), ("4", "IO2", pa)], right=[("5", "VBUS", pa), ("2", "GND", pa)])
S.def_ic("BQ24074RGT", width=17.78, left=[("13", "IN", pwi), ("6", "EN1", pi), ("5", "EN2", pi), ("4", "~{CE}", pi), ("12", "ILIM", pa), ("16", "ISET", pa),
    ("14", "TMR", pi), ("15", "ITERM", pi), ("1", "TS", pa)],
  right=[("10", "OUT", pwo), ("11", "OUT", pa), ("2", "BAT", pwo), ("3", "BAT", pa), ("7", "~{PGOOD}", oc), ("9", "~{CHG}", oc), None, ("8", "VSS", pwi), ("17", "EP", pa)])
S.def_ic("TPS63060", width=15.24, left=[("2", "VIN", pwi), ("3", "EN", pi), ("4", "PS/SYNC", pi), ("1", "L1", pa), ("10", "L2", pa)],
  right=[("9", "VOUT", pwo), ("8", "FB", pi), ("5", "PG", oc), ("6", "VAUX", pa), ("7", "GND", pwi), ("11", "PGND", pwi)])
S.def_ic("LM27762", width=15.24, left=[("3", "VIN", pwi), ("12", "EN+", pi), ("8", "EN-", pi), ("10", "C1+", pa), ("9", "C1-", pa), ("1", "PGOOD", pa)],
  right=[("11", "OUT+", pwo), ("2", "FB+", pi), ("6", "OUT-", pwo), ("7", "FB-", pi), ("5", "CP", pwo), ("4", "GND", pwi), ("13", "EP", pwi)])
S.def_ic("LDO_SOT23-5", width=12.7, left=[("1", "IN", pwi), ("3", "EN", pi)], right=[("5", "OUT", pwo), ("4", "NC", nc), ("2", "GND", pwi)])
S.def_ic("Conn_10", width=10.16, refp="J", left=[(str(i), str(i), pa) for i in range(1, 11)] + [("MP", "MP", pa)], right=[])
S.def_ic("Conn_6", width=10.16, refp="J", left=[(str(i), str(i), pa) for i in range(1, 7)] + [("MP", "MP", pa)], right=[])
S.def_ic("Conn_3", width=10.16, refp="J", left=[(str(i), str(i), pa) for i in range(1, 4)], right=[])
S.def_ic("Conn_2", width=10.16, refp="J", left=[("1", "1", pa), ("2", "2", pa)], right=[])
S.def_ic("Conn_2x8", width=12.7, refp="J", left=[(str(i), str(i), pa) for i in range(1, 17, 2)], right=[(str(i), str(i), pa) for i in range(2, 17, 2)])
S.def_ic("USB_C_PowerOnly", width=12.7, refp="J", left=[("A9", "VBUS", pa), ("B9", "VBUS", pa), ("A5", "CC1", pa), ("B5", "CC2", pa)],
  right=[("A12", "GND", pa), ("B12", "GND", pa), ("S1", "SHIELD", pa)])
S.def_ic("Crystal_4pin", width=10.16, refp="Y", left=[("1", "1", pa), ("3", "3", pa)], right=[("2", "GND", pa), ("4", "GND", pa)])
S.def_ic("SW_SPDT", width=10.16, refp="SW", left=[("2", "COM", pa)], right=[("1", "A", pa), ("3", "B", pa)])
S.def_ic("MountingHole", width=5.08, refp="H", left=[], right=[])

# ---- Teensy 4.0 sockets
S.add("J1", "Teensy40_L", "Teensy 4.0 left (GND,0..12)", "SOCK14", {"1": "GND", "2": "EXP_0", "3": "EXP_1", "4": "PTT_A_DRV", "5": "PTT_B_DRV",
    "6": "IOX_INT", "7": "CODEC_RST", "8": "HP_EN", "9": "TDM_TX_T", "10": "TDM_RX_T", "11": "ENC_BV_A", "12": "ENC_BV_B", "13": "ENC_BC_A", "14": "ENC_BC_B"},
    "1x14 2.54 mm female socket", "", "Hand-solder; Teensy 4.0 USB toward top edge")
S.add("J2", "Teensy40_R", "Teensy 4.0 right (VIN,GND,3V3,23..13)", "SOCK14", {"1": "+5V_TEENSY", "2": "GND", "3": None, "4": "TDM_MCLK_T", "5": "VBAT_SENSE",
    "6": "TDM_BCLK_T", "7": "TDM_FSYNC_T", "8": "I2C_SCL", "9": "I2C_SDA", "10": "ENC_AC_B", "11": "ENC_AC_A", "12": "ENC_AV_B", "13": "ENC_AV_A", "14": "EXP_13"},
    "1x14 2.54 mm female socket", "", "Teensy 3V3 output deliberately unused")
S.add("D1", "D", "B5819W", "SOD123", {"1": "+5V_TEENSY", "2": "+5V2"}, "B5819W Schottky 1 A 40 V", "C8598", "Blocks Teensy USB back-feed; still cut VUSB-VIN pad")
S.add("J3", "Conn_3", "USB HOST (wire to Teensy pads)", "HDR1x3", {"1": "USBH_DP", "2": "USBH_DM", "3": "GND"}, "1x3 2.54 mm header", "", "Two short wires from the Teensy 4.0 underside host pads")
S.R("R1", "33", "TDM_MCLK_T", "TDM_MCLK", "MCLK series, near Teensy")
S.R("R2", "33", "TDM_BCLK_T", "TDM_BCLK", "BCLK series, near Teensy")
S.R("R3", "33", "TDM_FSYNC_T", "TDM_FSYNC", "FSYNC series, near Teensy")
S.R("R4", "33", "TDM_TX_T", "TDM_TX", "TDM data to codec, near Teensy")
S.R("R5", "33", "TDM_RX", "TDM_RX_T", "TDM data from codec, near codec")
S.R("R6", "2.2k", "+3V3", "I2C_SDA", "I2C pull-up"); S.R("R7", "2.2k", "+3V3", "I2C_SCL", "I2C pull-up")
S.R("R8", "10k", "+3V3", "IOX_INT", "Expander INT pull-up")
S.R("R9", "100k", "VBAT", "VBAT_SENSE", "Battery divider"); S.R("R10", "100k", "VBAT_SENSE", "GND", "Battery divider")
S.C("C1", "100nF", "VBAT_SENSE", "GND", "Battery divider filter")

# ---- Codec
cn = {"3": "+5VA", "49": "+5VA", "14": "+5VA", "34": "+5VA", "46": "+3V3", "12": "+3V3",
      "41": "TDM_MCLK", "7": "TDM_BCLK", "36": "TDM_BCLK", "6": "TDM_FSYNC", "35": "TDM_FSYNC",
      "37": "TDM_TX", "38": "GND", "39": "GND", "40": "GND", "8": "TDM_RX", "9": None, "10": None,
      "42": "I2C_SCL", "43": "I2C_SDA", "44": "GND", "45": "GND", "48": "GND", "4": "CODEC_RST", "5": None, "13": None,
      "2": "GND", "50": "GND", "16": "GND", "33": "GND", "11": "GND", "47": "GND", "65": "GND",
      "52": "ADC1_P", "51": "ADC1_N", "54": "ADC2", "53": "ADC2", "56": "ADC3_P", "55": "ADC3_N",
      "58": "ADC4_P", "57": "ADC4_N", "62": "ADC5_P", "61": "ADC5_N", "64": "ADC6", "63": "ADC6",
      "1": "VCOMAD", "15": "VCOMDA", "59": "VREFAD1", "60": "VREFAD2",
      "31": "DAC1_P", "32": "DAC1_N", "29": "DAC2_P", "30": "DAC2_N", "27": "DAC3_P", "28": "DAC3_N", "25": "DAC4_P", "26": "DAC4_N",
      "23": "DAC5_P", "24": "DAC5_N", "21": None, "22": None, "19": None, "20": None, "17": None, "18": None}
S.add("U1", "PCM3168A", "PCM3168APAPR", "HTQFP64", cn, "TI PCM3168APAPR", "", "I2C addr 0x44 (ADR1=ADR0=0), MODE=GND (I2C)")
for i, pin in enumerate(["VCCAD1", "VCCAD2", "VCCDA1", "VCCDA2"]): S.C(f"C{10+i}", "1uF", "+5VA", "GND", f"U1 {pin}")
S.C("C14", "1uF", "+3V3", "GND", "U1 VDD1"); S.C("C15", "1uF", "+3V3", "GND", "U1 VDD2")
S.C("C16", "10uF", "+5VA", "GND", "U1 VCC bulk (AD side)", "C0805"); S.C("C17", "10uF", "+5VA", "GND", "U1 VCC bulk (DA side)", "C0805")
S.C("C18", "10uF", "+3V3", "GND", "U1 VDD bulk", "C0805")
S.C("C19", "10uF", "VCOMAD", "GND", "VCOMAD", "C0805"); S.C("C20", "10uF", "VCOMDA", "GND", "VCOMDA", "C0805")
S.C("C21", "10uF", "VREFAD1", "GND", "VREFAD1", "C0805"); S.C("C22", "10uF", "VREFAD2", "GND", "VREFAD2", "C0805")
S.C("C23", "1uF", "ADC6", "GND", "Unused ADC6 inputs terminated")

# ---- Headset mic: INA217
S.add("U2", "INA217_SOIC16", "INA217AIDWR", "SOIC16W", {"5": "MIC_P_F", "4": "MIC_N_F", "2": "INA_RG1", "15": "INA_RG2", "1": None, "3": None, "6": None, "8": None,
      "13": "+5VP", "7": "-5VP", "11": "MIC_PRE", "10": "GND", "9": None, "12": None, "14": None, "16": None}, "TI INA217AIDWR", "", "Mic preamp, G = 1 + 10k/RG")
S.R("R20", "47", "HS_MIC_P", "MIC_P_F", "Input stabilisation (datasheet 47 ohm)"); S.R("R21", "47", "HS_MIC_N", "MIC_N_F", "Input stabilisation")
S.R("R22", "10k", "MIC_P_F", "GND", "Input bias path"); S.R("R23", "10k", "MIC_N_F", "GND", "Input bias path")
S.C("C24", "1nF", "MIC_P_F", "MIC_N_F", "Differential RF filter", diel="C0G")
S.R("R24", "169", "INA_RG1", "INA_RG2", "RG: gain ~60 (36 dB)", mpn="Panasonic ERJ-3EKF1690V (1%, 100 ppm)", lcsc="C403019")
S.R("R25", "DNP", "INA_RG1", "INA_RG2", "Gain trim: fit a RESISTOR in parallel with R24 for more gain (never 0 ohm)", dnp=True, mpn="not fitted")
S.add("D2", "BAV99", "BAV99", "SOT23", {"3": "MIC_P_F", "2": "+5VP", "1": "-5VP"}, "BAV99 dual diode", "C2500", "Mic input clamp to rails")
S.add("D3", "BAV99", "BAV99", "SOT23", {"3": "MIC_N_F", "2": "+5VP", "1": "-5VP"}, "BAV99 dual diode", "C2500", "Mic input clamp to rails")
S.C("C25", "100nF", "+5VP", "GND", "U2 V+"); S.C("C26", "100nF", "-5VP", "GND", "U2 V-")
S.C("C27", "10uF", "MIC_PRE", "MIC_AC", "AC coupling", "C0805")
S.R("R28", "1k", "MIC_AC", "ADC3_P", "ADC input RC (with C29: ~59 kHz)")
S.C("C29", "2.7nF", "ADC3_P", "ADC3_N", "ADC input RC / RF filter", diel="C0G")
S.R("R26", "100k", "ADC3_P", "VCOMAD", "ADC3+ bias"); S.R("R27", "100k", "ADC3_N", "VCOMAD", "ADC3- bias")
S.C("C28", "1uF", "ADC3_N", "GND", "ADC3- AC ground (pseudo-differential)")

# ---- Radio RX front ends (A -> ADC2, B -> ADC3) and TX drivers (DAC3/DAC4 via OPA1678), PTT, ground lift
def radio(tag, adc, dac_p, dac_n, ch, r0, c0, d0):
    T = tag  # "RA" / "RB"
    S.C(f"C{c0}", "1uF", f"{T}_RX", f"{T}_RX_C", f"{T} RX AC coupling")
    S.C(f"C{c0+1}", "1uF", f"{T}_RXR", f"{T}_RXR_C", f"{T} RX return AC coupling")
    S.R(f"R{r0}", "10k", f"{T}_RX_C", f"{adc}_P", f"{T} RX series"); S.R(f"R{r0+1}", "10k", f"{T}_RXR_C", f"{adc}_N", f"{T} RX return series")
    S.R(f"R{r0+2}", "100k", f"{adc}_P", "VCOMAD", "ADC bias"); S.R(f"R{r0+3}", "100k", f"{adc}_N", "VCOMAD", "ADC bias")
    S.C(f"C{c0+2}", "1nF", f"{adc}_P", f"{adc}_N", "Differential RF filter", diel="C0G")
    S.R(f"R{r0+4}", "2.2k", f"{adc}_P", f"{adc}_N", "Optional RX divider with the 2x10k series R (~-20 dB) for speaker-level sources", dnp=True)
    # TX diff-to-SE (gain 0.25, 0.1 % resistors), output AC-coupled, attenuated to mic level
    S.R(f"R{r0+5}", "20k", dac_n, f"{T}_TX_INV", "TX diff amp input", "0.1%", mpn="Yageo RT0603BRD0720KL (0.1%, 25 ppm)")
    S.R(f"R{r0+6}", "4.99k", f"{T}_TX_INV", f"{T}_TX_OUT", "TX diff amp feedback", "0.1%", mpn="Yageo RT0603BRD074K99L (0.1%, 25 ppm)")
    S.R(f"R{r0+7}", "20k", dac_p, f"{T}_TX_NI", "TX diff amp input", "0.1%", mpn="Yageo RT0603BRD0720KL (0.1%, 25 ppm)")
    S.R(f"R{r0+8}", "4.99k", f"{T}_TX_NI", "GND", "TX diff amp reference leg", "0.1%", mpn="Yageo RT0603BRD074K99L (0.1%, 25 ppm)")
    S.C(f"C{c0+3}", "1nF", f"{T}_TX_INV", f"{T}_TX_OUT", "TX LPF (~32 kHz)", diel="C0G")
    S.C(f"C{c0+4}", "1nF", f"{T}_TX_NI", "GND", "TX LPF mirror", diel="C0G")
    S.R(f"R{r0+9}", "1k", f"{T}_TX_OUT", f"{T}_TX_A", "TX attenuator series")
    S.R(f"R{r0+10}", "100", f"{T}_TX_A", f"{T}_TXR", "TX attenuator shunt (~64 mV FS); radio-specific")
    S.C(f"C{c0+5}", "10uF", f"{T}_TX_A", f"{T}_TX", "TX DC block: radio mic bias sees only this cap", "C0805")
    # ground lift: bridged solder jumper with 10 ohm alongside
    S.R(f"R{r0+15}", "0", f"{T}_TXR", "GND", f"Ground tie: remove to lift {T} port ground to 10 ohm")
    S.R(f"R{r0+11}", "10", f"{T}_TXR", "GND", "Ground-lift resistor")
    # ESD
    S.add(f"D{d0}", "TVS_BI", "PESD5V0L1BA", "SOD323", {"1": f"{T}_RX", "2": "GND"}, "Nexperia PESD5V0L1BA bidirectional", "", "ESD")
    S.add(f"D{d0+1}", "TVS_BI", "PESD5V0L1BA", "SOD323", {"1": f"{T}_RXR", "2": "GND"}, "Nexperia PESD5V0L1BA bidirectional", "", "ESD")
    S.add(f"D{d0+2}", "TVS_BI", "PESD5V0L1BA", "SOD323", {"1": f"{T}_TX", "2": "GND"}, "Nexperia PESD5V0L1BA bidirectional", "", "ESD")
    S.add(f"D{d0+3}", "TVS_BI", "SMF15CA", "SOD123F", {"1": f"{T}_PTT", "2": f"{T}_PTTR"}, "SMF15CA bidirectional TVS (VRWM 15 V, VC 24.4 V @ 8.2 A)", "", "Across PTT contact; clamps well under AQY212GS 60 V")
    # PTT
    S.R(f"R{r0+12}", "1k", f"PTT_{tag[1]}_DRV", f"{T}_PTT_G", "Gate series"); S.R(f"R{r0+13}", "100k", f"{T}_PTT_G", "GND", "Gate pull-down: PTT off at reset")
    S.add(f"Q{ch}", "2N7002", "2N7002", "SOT23", {"1": f"{T}_PTT_G", "3": f"{T}_PTT_K", "2": "GND"}, "2N7002 N-MOSFET", "C8545", "PhotoMOS LED driver")
    S.R(f"R{r0+14}", "330", "+3V3", f"{T}_PTT_LED", "PhotoMOS LED ~6 mA")
    S.add(f"K{ch}", "AQY212GS", "AQY212GS", "SOP4", {"1": f"{T}_PTT_LED", "2": f"{T}_PTT_K", "4": f"{T}_PTT", "3": f"{T}_PTTR"},
          "Panasonic AQY212GS PhotoMOS", "C719745", "Isolated PTT contact (AC/DC)")
    S.add(f"TP{ch+10}", "TP", f"PTT_{tag[1]}", "TP", {"1": f"PTT_{tag[1]}_DRV", "2": None}, "test point", "", "")
radio("RA", "ADC4", "DAC3_P", "DAC3_N", 1, 30, 30, 10)
radio("RB", "ADC5", "DAC4_P", "DAC4_N", 2, 50, 40, 20)
S.add("U3", "OPA1678", "OPA1678IDR", "SOIC8", {"3": "RA_TX_NI", "2": "RA_TX_INV", "1": "RA_TX_OUT", "5": "RB_TX_NI", "6": "RB_TX_INV", "7": "RB_TX_OUT",
      "8": "+5VP", "4": "-5VP"}, "TI OPA1678IDR", "", "Radio A/B TX drivers")
S.C("C50", "100nF", "+5VP", "GND", "U3 V+"); S.C("C51", "100nF", "-5VP", "GND", "U3 V-")

# ---- Headset amp OPA1622 (DAC1 -> L, DAC2 -> R), gain 0.733 DC-coupled per PCM3168A app circuit
S.add("U4", "OPA1622", "OPA1622IDRCR", "VSON10_1622", {"1": "HPA_NI", "10": "HPA_INV", "5": "HPB_NI", "6": "HPB_INV", "8": "HP_EN",
      "2": "+5VP", "9": "HPA_OUT", "7": "HPB_OUT", "3": "GND", "4": "-5VP", "11": "-5VP"}, "TI OPA1622IDRCR", "C2876559", "Headset driver")
for ch, dp, dn, base in (("A", "DAC1_P", "DAC1_N", 70), ("B", "DAC2_P", "DAC2_N", 75)):
    S.R(f"R{base}", "15k", dn, f"HP{ch}_INV", "HP diff amp input", "0.1%", mpn="Yageo RT0603BRD0715KL (0.1%, 25 ppm)", lcsc="C326733")
    S.R(f"R{base+1}", "11k", f"HP{ch}_INV", f"HP{ch}_OUT", "HP diff amp feedback", "0.1%", mpn="FH TD03G1102BT (0.1%, 25 ppm; alt Yageo RT0603BRD0711KL)", lcsc="C667038")
    S.R(f"R{base+2}", "15k", dp, f"HP{ch}_NI", "HP diff amp input", "0.1%", mpn="Yageo RT0603BRD0715KL (0.1%, 25 ppm)", lcsc="C326733")
    S.R(f"R{base+3}", "11k", f"HP{ch}_NI", "GND", "HP diff amp reference leg", "0.1%", mpn="FH TD03G1102BT (0.1%, 25 ppm; alt Yageo RT0603BRD0711KL)", lcsc="C667038")
    S.R(f"R{base+4}", "10", f"HP{ch}_OUT", "HS_SPK_L" if ch == "A" else "HS_SPK_R", "Output isolation")
S.C("C60", "330pF", "HPA_INV", "HPA_OUT", "HP LPF", diel="C0G"); S.C("C61", "330pF", "HPA_NI", "GND", "HP LPF mirror", diel="C0G")
S.C("C62", "330pF", "HPB_INV", "HPB_OUT", "HP LPF", diel="C0G"); S.C("C63", "330pF", "HPB_NI", "GND", "HP LPF mirror", diel="C0G")
S.R("R80", "100k", "HP_EN", "GND", "Amp held off until firmware drives HP_EN (Teensy pin 6)")
S.C("C65", "100nF", "+5VP", "GND", "U4 V+"); S.C("C66", "100nF", "-5VP", "GND", "U4 V-")
S.C("C67", "10uF", "+5VP", "GND", "U4 V+ bulk", "C0805"); S.C("C68", "10uF", "-5VP", "GND", "U4 V- bulk", "C0805")

# ---- Headers
S.add("J10", "Conn_10", "RADIO A (JST-GH 10)", "GH10", {"1": "RA_RX", "2": "RA_RXR", "3": "RA_TX", "4": "RA_TXR", "5": "RA_PTT", "6": "RA_PTTR",
      "7": "USB_A_DP", "8": "USB_A_DM", "9": "RA_VBUS", "10": "GND", "MP": "GND"}, "JST BM10B-GHS-TBT", "", "Hand-solder")
S.add("J11", "Conn_10", "RADIO B (JST-GH 10)", "GH10", {"1": "RB_RX", "2": "RB_RXR", "3": "RB_TX", "4": "RB_TXR", "5": "RB_PTT", "6": "RB_PTTR",
      "7": "USB_B_DP", "8": "USB_B_DM", "9": "RB_VBUS", "10": "GND", "MP": "GND"}, "JST BM10B-GHS-TBT", "", "Hand-solder")
S.add("J12", "Conn_6", "HEADSET (JST-GH 6)", "GH6", {"1": "HS_MIC_P", "2": "HS_MIC_N", "3": "HS_SPK_L", "4": "HS_SPK_R", "5": "GND", "6": "HS_SHLD", "MP": "GND"},
      "JST BM06B-GHS-TBT", "", "Hand-solder")
S.R("R81", "0", "HS_SHLD", "GND", "Headset shield tie (lift-able)")
S.add("J13", "Conn_2x8", "FRONT PANEL (2x8 1.27)", "IDC2x8", {"1": "+3V3", "2": "+3V3", "3": "GND", "4": "GND", "5": "I2C_SDA", "6": "I2C_SCL", "7": "IOX_INT",
      "8": "GND", "9": "ENC_AV_A", "10": "ENC_AV_B", "11": "ENC_AC_A", "12": "ENC_AC_B", "13": "ENC_BV_A", "14": "ENC_BV_B", "15": "ENC_BC_A", "16": "ENC_BC_B"},
      "2x8 1.27 mm header", "", "IDC ribbon to front panel")
S.add("J14", "Conn_2x8", "AUX (2x8 2.54)", "HDR2x8", {"1": "+3V3", "2": "+5V2", "3": "GND", "4": "GND", "5": "EXP_0", "6": "EXP_1", "7": "GND", "8": "EXP_13",
      "9": "AUX_ADC1_P", "10": "AUX_ADC1_N", "11": "GND", "12": "GND", "13": "AUX_DAC5_P", "14": "AUX_DAC5_N", "15": "GND", "16": "GND"},
      "2x8 2.54 mm header", "", "Expansion: Teensy spares + codec spares")
S.C("C72", "1uF", "ADC2", "GND", "Unused ADC2 inputs terminated")
for k, (adc, rb) in enumerate((("ADC1", 90),)):
    S.C(f"C{70 + 2*k}", "1uF", f"AUX_{adc}_P", f"AUX_{adc}_P_C", "Aux ADC AC coupling"); S.C(f"C{71 + 2*k}", "1uF", f"AUX_{adc}_N", f"AUX_{adc}_N_C", "Aux ADC AC coupling")
    S.R(f"R{rb}", "10k", f"AUX_{adc}_P_C", f"{adc}_P", "Aux series"); S.R(f"R{rb+1}", "10k", f"AUX_{adc}_N_C", f"{adc}_N", "Aux series")
    S.R(f"R{rb+2}", "100k", f"{adc}_P", "VCOMAD", "ADC bias"); S.R(f"R{rb+3}", "100k", f"{adc}_N", "VCOMAD", "ADC bias")
S.R("R102", "100", "DAC5_P", "AUX_DAC5_P", "Aux DAC series"); S.R("R103", "100", "DAC5_N", "AUX_DAC5_N", "Aux DAC series")

# ---- USB hub FE1.1s + per-port VBUS switch + ESD
S.add("U5", "FE1.1s", "FE1.1S-BSOP28BCN", "SSOP28", {"20": "+5V2", "21": "HUB_3V3", "13": "HUB_3V3", "12": "HUB_1V8", "28": "HUB_1V8",
      "3": "HUB_XI", "2": "HUB_XO", "14": "HUB_REXT", "17": "HUB_RST", "18": "HUB_VBM", "19": "HUB_3V3",
      "22": None, "23": None, "24": None, "25": "HUB_PWRJ", "26": "HUB_OVC", "27": None, "1": "GND",
      "16": "USBH_DP", "15": "USBH_DM", "11": "USB_B_DP", "10": "USB_B_DM", "9": "USB_A_DP", "8": "USB_A_DM",
      "7": None, "6": None, "5": None, "4": None}, "Terminus FE1.1S-BSOP28BCN", "C9359", "Self-powered (BUSJ high); ports 3/4 unused")
S.add("Y1", "Crystal_4pin", "12MHz", "XTAL", {"1": "HUB_XI", "3": "HUB_XO", "2": "GND", "4": "GND"}, "YXC X322512MSB4SI (12 MHz 3225, 20 pF, +/-10 ppm)", "C9002", "FE1.1s has internal load caps")
S.C("C80", "10pF", "HUB_XI", "GND", "Optional crystal load", diel="C0G", dnp=True); S.C("C81", "10pF", "HUB_XO", "GND", "Optional crystal load", diel="C0G", dnp=True)
S.R("R110", "2.7k", "HUB_REXT", "GND", "REXT 2.7k 1% (datasheet)")
S.R("R111", "10k", "HUB_3V3", "HUB_RST", "Reset pull-up"); S.C("C82", "100nF", "HUB_RST", "GND", "Reset RC")
S.R("R112", "4.7k", "+5V2", "HUB_VBM", "VBUSM divider (~3.4 V)"); S.R("R113", "10k", "HUB_VBM", "GND", "VBUSM divider")
S.R("R114", "10k", "HUB_3V3", "HUB_OVC", "OVCJ pull-up")
S.R("R115", "10k", "HUB_3V3", "HUB_PWRJ", "PWRJ pull-up: ports off until the hub enables them")
S.C("C83", "10uF", "+5V2", "GND", "Hub VDD5", "C0805"); S.C("C84", "100nF", "+5V2", "GND", "Hub VDD5")
S.C("C85", "10uF", "HUB_3V3", "GND", "VD33 (datasheet 10 uF)", "C0805"); S.C("C86", "100nF", "HUB_3V3", "GND", "VD33")
S.C("C87", "10uF", "HUB_1V8", "GND", "VD18 (datasheet 10 uF)", "C0805"); S.C("C88", "100nF", "HUB_1V8", "GND", "VD18")
for tag, port, uS, uE, cS in (("RA", "A", "U6", "U8", 90), ("RB", "B", "U7", "U9", 93)):
    S.add(uS, "TPS2552", "TPS2552DBVR", "SOT23-6", {"1": "+5V2", "3": "HUB_PWRJ", "5": f"{tag}_ILIM", "6": f"{tag}_VBUS", "4": "HUB_OVC", "2": "GND"},
          "TI TPS2552DBVR adjustable limit, ACTIVE-LOW EN", "", f"Radio {port} VBUS: on when hub PWRJ is low; ganged with the other port")
    S.R(f"R{116 if port == 'A' else 117}", "45.3k", f"{tag}_ILIM", "GND", "RILIM 45.3k 1%: 0.519 A min (R+1%) / 0.644 A max (R-1%), TPS2552/3 datasheet eq. 1 and 3", mpn="Viking ARG03FTC4532 (1% thin film, 25 ppm; alt Bourns CR0603-FX-4532ELF C49675646)", lcsc="C218038")
    S.C(f"C{cS}", "100nF", "+5V2", "GND", f"{uS} IN"); S.C(f"C{cS+1}", "10uF", f"{tag}_VBUS", "GND", f"Radio {port} VBUS", "C0805")
    S.add(uE, "USBLC6-2SC6", "USBLC6-2SC6", "SOT23-6", {"1": f"USB_{port}_DP", "6": f"USB_{port}_DP", "3": f"USB_{port}_DM", "4": f"USB_{port}_DM",
          "5": f"{tag}_VBUS", "2": "GND"}, "ST USBLC6-2SC6", "C7519", f"Radio {port} USB ESD")

# ---- Power: USB-C in, BQ24074 charger, battery, switch, TPS63060 5.2 V, LM27762 +/-5 V, NCP163 5 V, TLV75533 3.3 V
S.add("J15", "USB_C_PowerOnly", "USB-C 5V IN", "USBC", {"A9": "VBUS_IN", "B9": "VBUS_IN", "A5": "CC1", "B5": "CC2", "A12": "GND", "B12": "GND", "S1": "GND"},
      "GCT USB4125-GF-A-0190 (power only)", "", "")
S.add("U15", "TUSB321", "TUSB321RWBR", "X2QFN12", {"12": "VBUS_IN", "5": "CC_VDET", "1": "CC1", "2": "CC2", "4": "GND", "3": "GND",
      "7": "CC_HI_N", "8": None, "9": None, "6": None, "11": None, "10": "GND"}, "TI TUSB321RWBR", "", "UFP: presents Rd; OUT1 low = source offers >= 1.5 A")
S.R("R120", "910k", "VBUS_IN", "CC_VDET", "VBUS_DET (datasheet 855-920k)", mpn="Bourns CR0603-FX-9103ELF (1%; alt RESI AECR0603F910KK9 C352285)", lcsc="C203887")
S.R("R121", "100k", "VBUS_IN", "CC_HI_N", "OUT1 pull-up")
S.C("C119", "1uF", "VBUS_IN", "GND", "TUSB321 VDD")
S.add("Q3", "2N7002", "2N7002", "SOT23", {"1": "CC_HI_N", "3": "CHG_EN2", "2": "GND"}, "2N7002 N-MOSFET", "C8545", "Inverter: EN2 = NOT OUT1")
S.R("R134", "100k", "VBUS_IN", "CHG_EN2", "EN2 pull-up")
S.add("D30", "D", "SMF5.0A", "SOD123F", {"1": "VBUS_IN", "2": "GND"}, "SMF5.0A TVS 5 V", "C78395", "USB-C VBUS surge")
S.add("U10", "BQ24074RGT", "BQ24074RGTR", "VQFN16TV", {"13": "VBUS_IN", "6": "CC_HI_N", "5": "CHG_EN2", "4": "GND", "12": "CHG_ILIM", "16": "CHG_ISET",
      "14": None, "15": None, "1": "CHG_TS", "10": "SYS", "11": "SYS", "2": "VBAT", "3": "VBAT", "7": None, "9": "CHG_LED_K", "8": "GND", "17": "GND"},
      "TI BQ24074RGTR", "", "500 mA by default; ILIM (1.3 A) only when the USB-C source advertises >= 1.5 A")
S.R("R122", "1.24k", "CHG_ILIM", "GND", "ILIM: 1610/1.24k = 1.30 A (stays under a 1.5 A advertisement with tolerance)", mpn="Vishay CRCW06031K24FKEA (1%; alt FH RS-03K1241FT C321702)", lcsc="C843923"); S.R("R123", "1k", "CHG_ISET", "GND", "ISET: 890/1k = 0.89 A charge")
S.R("R124", "10k", "CHG_TS", "GND", "Fit ONLY if the cell has no NTC (disables temperature protection)", dnp=True)
S.add("D31", "LED", "RED", "LED0805", {"1": "CHG_LED_K", "2": "CHG_LED_A"}, "0805 red LED", "C84256", "Charging indicator")
S.R("R125", "1k", "VBUS_IN", "CHG_LED_A", "CHG LED")
S.C("C100", "4.7uF", "VBUS_IN", "GND", "Charger IN", "C0805"); S.C("C101", "10uF", "SYS", "GND", "Charger OUT", "C0805")
S.C("C102", "10uF", "VBAT", "GND", "Charger BAT", "C0805")
S.add("J16", "Conn_3x", "18650 + NTC (Micro-Fit 3.0)", "MF3", {"1": "VBAT", "2": "GND", "3": "CHG_TS"}, "Molex 43650-0315 Micro-Fit 3.0 vertical", "", "Protected 18650 with 10k NTC: 1 = +, 2 = -, 3 = NTC. Rated 5 A/contact (18-20 AWG)")
S.add("SW1", "SW_SPDT", "POWER", "SW_SPDT", {"2": "PWR_EN", "1": "SYS", "3": None}, "C&K PCM12SMTR slide switch", "", "On/off; charging works when off")
S.R("R126", "1M", "PWR_EN", "GND", "Keeps the converter off when switched off")
S.add("U11", "TPS61230DRC", "TPS61230DRCR", "PVSON10TV", {"10": "SYS", "9": "PWR_EN", "8": None, "6": "BB_SS", "1": "BB_SW", "2": "BB_SW",
      "3": "+5V2", "4": "+5V2", "7": "BB_FB", "5": None, "11": "GND"}, "TI TPS61230DRCR", "", "Sync boost, 4 A min valley limit, true load disconnect")
S.add("L1", "L", "1.0uH", "L4x4XAL", {"1": "SYS", "2": "BB_SW"}, "Coilcraft XAL4020-102MEC (1.0 uH, Isat 8.7 A); alt Bourns SRP4020TA-1R0M", "", "Isat must exceed the 6 A max current limit")
S.C("C103", "22uF", "SYS", "GND", "Boost IN (datasheet 22 uF)", "C0805"); S.C("C104", "10uF", "SYS", "GND", "Boost IN", "C0805")
S.C("C105", "22uF", "+5V2", "GND", "Boost OUT", "C0805"); S.C("C106", "22uF", "+5V2", "GND", "Boost OUT", "C0805"); S.C("C107", "22uF", "+5V2", "GND", "Boost OUT", "C0805")
S.C("C109", "1uF", "+5V2", "GND", "Boost OUT HF, at the VOUT pins")
S.C("C108", "10nF", "BB_SS", "GND", "Soft start (datasheet 10 nF)")
S.R("R127", "422k", "+5V2", "BB_FB", "FB: 1.0 x (1 + 422k/100k) = 5.22 V", mpn="RALEC RTT034223FTP (1%)", lcsc="C103627"); S.R("R128", "100k", "BB_FB", "GND", "FB bottom (<= 100k per datasheet)")
S.C("C120", "18pF", "+5V2", "BB_FB", "Feed-forward (datasheet example)", diel="C0G")
S.add("U12", "LM27762", "LM27762DSSR", "WSON12_27762", {"3": "+5V2", "12": "+5V2", "8": "+5V2", "10": "CP_C1P", "9": "CP_C1N", "1": "GND",
      "11": "+5VP", "2": "CP_FBP", "6": "-5VP", "7": "CP_FBN", "5": "CP_OUT", "4": "GND", "13": "GND"}, "TI LM27762DSSR", "C473398", "+/-5.0 V for INA217 / op-amps")
S.R("R129", "294k", "+5VP", "CP_FBP", "1.2 x (1 + 294k/100k) = 4.73 V (headroom from 5.22 V)", mpn="RALEC RTT032943FTP (1%; alt Vishay CRCW0603294KFKEA C2092132)", lcsc="C13177"); S.R("R130", "100k", "CP_FBP", "GND", "FB+ bottom")
S.R("R131", "287k", "-5VP", "CP_FBN", "-1.22 x (1 + 287k/100k) = -4.72 V", mpn="LIZ CR0603FA2873G (1%)", lcsc="C100934"); S.R("R132", "100k", "CP_FBN", "GND", "FB- bottom")
S.C("C110", "10uF", "+5V2", "GND", "LM27762 VIN", "C0805"); S.C("C111", "1uF", "CP_C1P", "CP_C1N", "Flying cap")
S.C("C112", "10uF", "CP_OUT", "GND", "CP output", "C0805"); S.C("C113", "2.2uF", "+5VP", "GND", "OUT+"); S.C("C114", "2.2uF", "-5VP", "GND", "OUT-")
S.add("U13", "LDO_SOT23-5", "NCP163ASN500T1G", "SOT23-5", {"1": "+5V2", "3": "+5V2", "5": "+5VA", "4": None, "2": "GND"}, "onsemi NCP163ASN500T1G", "", "Codec analog 5.0 V")
S.C("C115", "1uF", "+5V2", "GND", "NCP163 IN"); S.C("C116", "4.7uF", "+5VA", "GND", "NCP163 OUT", "C0805")
S.add("U14", "LDO_SOT23-5", "TLV75533PDBVR", "SOT23-5", {"1": "+5V2", "3": "+5V2", "5": "+3V3", "4": None, "2": "GND"}, "TI TLV75533PDBVR", "", "3.3 V digital")
S.C("C117", "1uF", "+5V2", "GND", "TLV755 IN"); S.C("C118", "1uF", "+3V3", "GND", "TLV755 OUT")
S.add("D32", "LED", "GREEN", "LED0805", {"1": "GND", "2": "PWR_LED_A"}, "0805 green LED", "C2297", "Power on")
S.R("R133", "2.2k", "+5V2", "PWR_LED_A", "Power LED")

# ---- test points + mounting holes
tps = [("TP1", "MCLK", "TDM_MCLK"), ("TP2", "BCLK", "TDM_BCLK"), ("TP3", "FSYNC", "TDM_FSYNC"), ("TP4", "TDM_TX", "TDM_TX"), ("TP5", "TDM_RX", "TDM_RX"),
       ("TP6", "RST", "CODEC_RST"), ("TP7", "+5V2", "+5V2"), ("TP8", "+3V3", "+3V3"), ("TP9", "+5VA", "+5VA"), ("TP10", "+5VP", "+5VP"),
       ("TP13", "-5VP", "-5VP"), ("TP14", "SYS", "SYS"), ("TP15", "VBAT", "VBAT"), ("TP16", "GND", "GND"), ("TP17", "GND", "GND")]
for ref, val, net in tps: S.add(ref, "TP", val, "TP", {"1": net, "2": None}, "test point", "", "")
for i in range(1, 5): S.add(f"H{i}", "MountingHole", "M2.5", "MH", {}, "", "", "")

blocks = [
 ("TEENSY 4.0 SOCKETS, CLOCK SERIES R, I2C, HOST WIRES", 20, 60, ["J1", "J2", "J3", "D1", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "C1"], 6),
 ("CODEC PCM3168A (TDM slave, I2C 0x44)", 20, 240, ["U1", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20", "C21", "C22", "C23"], 4),
 ("HEADSET MIC PREAMP INA217", 330, 60, ["U2", "R20", "R21", "R22", "R23", "C24", "R24", "R25", "D2", "D3", "C25", "C26", "C27", "R26", "R27", "C28", "R28", "C29"], 6),
 ("HEADSET AMP OPA1622 (DAC1 L, DAC2 R)", 330, 250, ["U4"] + [f"R{b+i}" for b in (70, 75) for i in range(5)] + ["C60", "C61", "C62", "C63", "R80", "C65", "C66", "C67", "C68"], 7),
 ("RADIO A: RX DIFF IN, TX DRIVER, PTT, GROUND LIFT", 20, 470, ["J10", "K1", "Q1"] + [f"R{30+i}" for i in range(16)] + [f"C{30+i}" for i in range(6)] + ["D10", "D11", "D12", "D13", "TP11"], 9),
 ("RADIO B: RX DIFF IN, TX DRIVER, PTT, GROUND LIFT", 20, 640, ["J11", "K2", "Q2", "U3", "C50", "C51"] + [f"R{50+i}" for i in range(16)] + [f"C{40+i}" for i in range(6)] + ["D20", "D21", "D22", "D23", "TP12"], 9),
 ("USB HUB FE1.1s, RADIO VBUS SWITCHES, ESD", 560, 470, ["U5", "Y1", "U6", "U7", "U8", "U9", "C80", "C81", "R110", "R111", "C82", "R112", "R113", "R114", "C83", "C84", "C85", "C86", "C87", "C88", "R116", "R117", "C90", "C91", "C93", "C94", "R115"], 6),
 ("POWER: USB-C + TUSB321 current detect, BQ24074, 18650, SWITCH, TPS61230 5.2 V BOOST", 630, 60, ["J15", "U15", "Q3", "U10", "J16", "SW1", "U11", "L1", "R120", "R121", "C119", "R134", "C109", "C120", "D30", "R122", "R123", "R124", "D31", "R125", "C100", "C101", "C102", "R126", "C103", "C104", "C105", "C106", "C107", "C108", "R127", "R128"], 7),
 ("ANALOG RAILS: LM27762 +/-5 V, NCP163 5.0 V, TLV75533 3.3 V", 630, 290, ["U12", "U13", "U14", "R129", "R130", "R131", "R132", "C110", "C111", "C112", "C113", "C114", "C115", "C116", "C117", "C118", "D32", "R133"], 6),
 ("HEADERS, AUX, TEST POINTS, MOUNTING", 560, 640, ["J12", "J13", "J14", "R81", "C70", "C71", "C72"] + [f"R{90+i}" for i in range(4)] + ["R102", "R103"] + [t[0] for t in tps] + ["H1", "H2", "H3", "H4"], 12),
]
S.layout(blocks)
S.emit(f"{OUTROOT}/radio_carrier", flags=("GND", "VBUS_IN", "+5V_TEENSY"),
       texts=[("Notes: cut the Teensy 4.0 VUSB-VIN pad. Codec MCLK = BCLK = 256 fs (8 x 32-bit TDM): firmware MUST set SRDA/SRAD = single rate (auto mode reads 256 fs as dual rate).", 20, 25, 2.0)])

# =================================================================== FRONT PANEL
F = Sheet("radio_frontpanel", "Dual-Radio PTT Front Panel - 4 encoders, 2 PTT, TCA9555", "A2")
F.def_ic("Conn_2x8", width=12.7, refp="J", left=[(str(i), str(i), pa) for i in range(1, 17, 2)], right=[(str(i), str(i), pa) for i in range(2, 17, 2)])
F.def_ic("TCA9555", width=17.78, left=[("24", "VCC", pwi), ("22", "SCL", pi), ("23", "SDA", bi), ("1", "~{INT}", oc), ("21", "A0", pi), ("2", "A1", pi), ("3", "A2", pi), None, ("12", "GND", pwi)],
  right=[("4", "P00", bi), ("5", "P01", bi), ("6", "P02", bi), ("7", "P03", bi), ("8", "P04", bi), ("9", "P05", bi), ("10", "P06", bi), ("11", "P07", bi),
         ("13", "P10", bi), ("14", "P11", bi), ("15", "P12", bi), ("16", "P13", bi), ("17", "P14", bi), ("18", "P15", bi), ("19", "P16", bi), ("20", "P17", bi)])
F.def_ic("Encoder_SW", width=12.7, refp="ENC", left=[("A", "A", pa), ("C", "C", pa), ("B", "B", pa)], right=[("S1", "S1", pa), ("S2", "S2", pa), ("SH", "SH", pa)])
F.def_ic("MountingHole", width=5.08, refp="H", left=[], right=[])
F.add("J1", "Conn_2x8", "TO CARRIER (2x8 1.27)", "IDC2x8", {"1": "+3V3", "2": "+3V3", "3": "GND", "4": "GND", "5": "I2C_SDA", "6": "I2C_SCL", "7": "IOX_INT",
      "8": "GND", "9": "ENC_AV_A", "10": "ENC_AV_B", "11": "ENC_AC_A", "12": "ENC_AC_B", "13": "ENC_BV_A", "14": "ENC_BV_B", "15": "ENC_BC_A", "16": "ENC_BC_B"},
      "2x8 1.27 mm header", "", "Same pin map as carrier J13")
F.add("U1", "TCA9555", "TCA9555PWR", "TSSOP24", {"24": "+3V3", "22": "I2C_SCL", "23": "I2C_SDA", "1": "IOX_INT", "21": "GND", "2": "GND", "3": "GND", "12": "GND",
      "4": "SW_AV", "5": "SW_AC", "6": "SW_BV", "7": "SW_BC", "8": "PTT_A_BTN", "9": "PTT_B_BTN", "10": "BTN_AUX1", "11": "BTN_AUX2",
      "13": "LED_TXA_K", "14": "LED_TXB_K", "15": "LED_BR_K", "16": None, "17": None, "18": None, "19": None, "20": None}, "TI TCA9555PWR", "", "Addr 0x20")
F.C("C1", "100nF", "+3V3", "GND", "U1"); F.C("C2", "10uF", "+3V3", "GND", "Board bulk", "C0805")
for i, net in enumerate(["SW_AV", "SW_AC", "SW_BV", "SW_BC", "PTT_A_BTN", "PTT_B_BTN", "BTN_AUX1", "BTN_AUX2"]):
    F.R(f"R{1+i}", "10k", "+3V3", net, "Button pull-up")
encs = [("ENC1", "AV", "Radio A volume"), ("ENC2", "AC", "Radio A channel"), ("ENC3", "BV", "Radio B volume"), ("ENC4", "BC", "Radio B channel")]
r = 10; c = 10
for ref, tag, desc in encs:
    F.add(ref, "Encoder_SW", desc, "ENC", {"A": f"E{tag}_A", "B": f"E{tag}_B", "C": "GND", "S1": f"SW_{tag}", "S2": "GND", "SH": "GND"},
          "Bourns PEC12R-4217F-S0024 (17 mm flatted shaft, switch, 24 PPR)", "", desc)
    for ph in ("A", "B"):
        F.R(f"R{r}", "10k", "+3V3", f"E{tag}_{ph}", "Encoder pull-up (Bourns filter)")
        F.R(f"R{r+1}", "10k", f"E{tag}_{ph}", f"ENC_{tag}_{ph}", "Encoder series (Bourns filter)")
        F.C(f"C{c}", "10nF", f"ENC_{tag}_{ph}", "GND", "Encoder filter (Bourns filter)")
        r += 2; c += 1
F.add("SW1", "SW", "PTT A", "PUSH12", {"1": "PTT_A_BTN", "2": "GND"}, "12 mm tactile switch", "", "Radio A PTT")
F.add("SW2", "SW", "PTT B", "PUSH12", {"1": "PTT_B_BTN", "2": "GND"}, "12 mm tactile switch", "", "Radio B PTT")
F.add("SW3", "SW", "AUX1", "PUSH6", {"1": "BTN_AUX1", "2": "GND"}, "6 mm tactile switch", "", "Spare (e.g. bridge)")
F.add("SW4", "SW", "AUX2", "PUSH6", {"1": "BTN_AUX2", "2": "GND"}, "6 mm tactile switch", "", "Spare")
for i, (k, a, col, lc) in enumerate([("LED_TXA_K", "LED_TXA_A", "RED", "C84256"), ("LED_TXB_K", "LED_TXB_A", "RED", "C84256"), ("LED_BR_K", "LED_BR_A", "AMBER", "C84262")]):
    F.add(f"D{1+i}", "LED", col, "LED0805", {"1": k, "2": a}, ("NationStar NCD0805O1 (amber/orange 605 nm)" if col == "AMBER" else f"0805 {col.lower()} LED"), lc, ["TX A", "TX B", "Bridge"][i])
    F.R(f"R{30+i}", "1k", "+3V3", a, "LED current")
for i in range(1, 5): F.add(f"H{i}", "MountingHole", "M2.5", "MH", {}, "", "", "")
F.layout([
 ("RIBBON + EXPANDER (TCA9555 @ 0x20)", 20, 40, ["J1", "U1", "C1", "C2"] + [f"R{1+i}" for i in range(8)], 4),
 ("ENCODERS (A/B: 10k pull-up, 10k series, 10 nF per Bourns)", 20, 200, ["ENC1", "ENC2", "ENC3", "ENC4"] + [f"R{10+i}" for i in range(16)] + [f"C{10+i}" for i in range(8)], 8),
 ("PTT + AUX BUTTONS, TX/BRIDGE LEDS", 20, 330, ["SW1", "SW2", "SW3", "SW4", "D1", "D2", "D3", "R30", "R31", "R32", "H1", "H2", "H3", "H4"], 8),
])
F.emit(f"{OUTROOT}/radio_frontpanel", flags=("GND", "+3V3"))
print("carrier parts", len(S.parts), "pins", len(S.expect), "| front panel parts", len(F.parts), "pins", len(F.expect))
