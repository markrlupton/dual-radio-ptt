import re,json,sys
from collections import defaultdict
d=sys.argv[1]; b=d.rstrip('/').split('/')[-1]
net=open(f"{d}/{b}.net").read(); exp=json.load(open(f"{d}/expected_nets.json"))
got={}
for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)',net,re.S):
    name=m.group(1).lstrip('/')
    for r,p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)',m.group(2)): got[f"{r}.{p}"]=name
bad=[(k,v,got.get(k)) for k,v in exp.items() if got.get(k)!=v]
# also map net groups: expected nets must not merge
g=defaultdict(set)
for k,v in exp.items():
    if k in got: g[got[k]].add(v)
merged={k:v for k,v in g.items() if len(v)>1}
print(b,"pins exp",len(exp),"got",len(got),"mismatch",len(bad),"merged",len(merged))
for x in bad[:20]: print(" ",x)
for k,v in list(merged.items())[:10]: print(" M",k,v)
