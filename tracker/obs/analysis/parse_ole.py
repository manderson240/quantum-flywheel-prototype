"""Structural parse of OLE QASM3 circuits (no simulation)."""
import re, sys, collections, math
def parse(path):
    ops=[]; seg=0
    for line in open(path):
        line=line.strip()
        if line.startswith('barrier'): seg+=1; continue
        m=re.match(r'^(\w+)(\(([^)]*)\))?\s+(q\[\d+\](?:,\s*q\[\d+\])*);',line)
        if not m or m.group(1) in ('gate','qubit','include','OPENQASM'): continue
        qs=[int(x) for x in re.findall(r'q\[(\d+)\]',m.group(4))]
        ang=None
        if m.group(3): ang=eval(m.group(3),{'pi':math.pi})
        ops.append((m.group(1),ang,tuple(qs),seg))
    return ops
if __name__=='__main__':
    for p in sys.argv[1:]:
        ops=parse(p); used=sorted({q for o in ops for q in o[2]})
        cz=[o for o in ops if o[0]=='cz']; E=collections.Counter(tuple(sorted(o[2])) for o in cz)
        deg=collections.Counter(); [deg.update(e) for e in E]
        print('==',p.split('/')[-1]); print(' qubits',len(used),'cz',len(cz),'distinct edges',len(E),'deg hist',collections.Counter(deg.values()),'segments',ops[-1][3]+1)
        rx=collections.Counter((round(o[1],6),) for o in ops if o[0]=='rx'); print(' rx angles',dict(rx))
        rz=collections.Counter(round(o[1],6) for o in ops if o[0]=='rz'); print(' rz angles',dict(rz))
        # rx angle sequence per qubit
        seq=collections.defaultdict(list)
        for o in ops:
            if o[0]=='rx': seq[o[2][0]].append(round(o[1]/math.pi,4))
        cls=collections.Counter(tuple(v) for v in seq.values())
        for k,v in cls.items(): print('  rx-seq x%d:'%v, k)
        others=[o for o in ops if o[0] not in('rx','rz','cz')]
        print(' other gates on',sorted({o[2][0] for o in others}))
