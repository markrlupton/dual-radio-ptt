import pcbnew,sys,re
from collections import Counter
b=pcbnew.LoadBoard(sys.argv[1]); rpt=sys.argv[1].replace(".kicad_pcb","_drc.rpt")
pcbnew.WriteDRCReport(b,rpt,pcbnew.EDA_UNITS_MILLIMETRES,True)
t=open(rpt).read()
print(Counter(re.findall(r'^\[(\w+)\]',t,re.M)))
print(re.findall(r'\*\* Found \d+ [^\n]*',t))
