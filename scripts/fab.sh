#!/bin/bash
# fab.sh <outdir> <proj>   (board file <outdir>/<proj>.kicad_pcb)
set -e
D=$1; P=$2; B=$D/$P.kicad_pcb; F=$D/fab; mkdir -p $F/gerber
kicad-cli pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts -o $F/gerber/ $B >/dev/null
kicad-cli pcb export drill --format excellon --excellon-separate-th -o $F/gerber/ $B >/dev/null
kicad-cli pcb export pos --format csv --units mm --side both -o $F/${P}_pos_raw.csv $B >/dev/null
python3 - "$F/${P}_pos_raw.csv" "$F/${P}_CPL_JLC.csv" "$D/${P}_BOM_full.csv" "$F/${P}_rotation_check.csv" <<'PY'
import csv,sys,re
# JLC rotation corrections for KiCad stock footprints (the matthewlai/JLCKicadTools table that KiBot and the
# JLC plugins ship). Packages not listed keep KiCad's rotation. JLC's placement preview is the authority:
# every polarized part is listed in *_rotation_check.csv to be confirmed there before the order is released.
ROT=[(r"^SOT-23",180),(r"^SOT-223",180),(r"^SOIC-",270),(r"^SOP-(?!18_)",270),(r"^TSSOP-",270),(r"^LQFP-",270),
     (r"^TQFP-",270),(r"^(.*?_|V)?QFN-(16|20|24|28|40)(-|_|$)",270),(r"^MSOP-10_",270),(r"^DFN-",270)]
PIN1={"SOT-23":"pin 1 left-bottom (KiCad) - check dot/bevel","SOIC":"pin 1 dot, top-left at 0 deg in KiCad",
      "SOP-4":"PhotoMOS: pin 1 = LED anode, dot", "TSSOP":"pin 1 dot", "QFN":"pin 1 mark / chamfer",
      "QFP":"pin 1 dot, top-left at 0 deg in KiCad", "SSOP":"pin 1 dot", "SON":"pin 1 dot (EP symmetric)",
      "X2QFN":"pin 1 mark - tiny, check carefully", "D_SOD":"cathode band = pad 1 (left at 0 deg)",
      "LED":"cathode = pad 1; check the green T/polarity mark", "Crystal":"pin 1 corner; 4-pin, pins 2/4 GND",
      "USB_C":"mechanical - check shell over board edge", "JST":"latch side / pin 1", "SW_SPDT":"actuator to board edge",
      "L_Coilcraft":"non-polarized"}
r=list(csv.DictReader(open(sys.argv[1])))
dnp=set()
for row in csv.DictReader(open(sys.argv[3])):
    if row["Fitted"]=="DNP": dnp|=set(row["Designator"].split(","))
chk=[]
with open(sys.argv[2],"w",newline="") as f:
    w=csv.writer(f); w.writerow(["Designator","Mid X","Mid Y","Layer","Rotation"])
    for x in r:
        if x["Ref"].startswith(("TP","H","JP")) or x["Ref"] in dnp: continue
        rot=float(x["Rot"]); add=next((a for p,a in ROT if re.search(p,x["Package"])),0)
        new=(rot+add)%360
        w.writerow([x["Ref"],x["PosX"]+"mm",x["PosY"]+"mm","Top" if x["Side"]=="top" else "Bottom",f"{new:g}"])
        if not x["Package"].startswith(("R_0603","C_0603","C_0805","PinSocket","PinHeader","MountingHole")):
            note=next((v for k,v in PIN1.items() if k in x["Package"]),"check pin 1")
            chk.append([x["Ref"],x["Val"],x["Package"],f"{rot%360:g}",f"{add:g}",f"{new:g}","table" if add else "KiCad as-is",note])
with open(sys.argv[4],"w",newline="") as f:
    w=csv.writer(f); w.writerow(["Ref","Value","Footprint","KiCad rot","JLC offset","CPL rot","Source","Pin-1 check in JLC preview"])
    w.writerows(sorted(chk,key=lambda c:(c[6],c[0])))
PY
rm $F/${P}_pos_raw.csv
(cd $F/gerber && zip -q ../${P}_gerbers.zip *)
kicad-cli sch export pdf -o $F/${P}_schematic.pdf $D/$P.kicad_sch >/dev/null 2>&1
cp $D/${P}_BOM_JLC.csv $D/${P}_BOM_full.csv $F/
echo done $F
