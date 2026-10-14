import sys, collections
sys.path.insert(0,__file__.rsplit('/',1)[0])
from parse_ole import parse
def wires(ops,neg=False):
    w=collections.defaultdict(list)
    for g,a,q,s in ops:
        for x in q: w[x].append((g, None if a is None else round(-a if neg else a,6), tuple(y for y in q if y!=x)))
    return w
for p in sys.argv[1:]:
    ops=parse(p); bidx=[i for i,o in enumerate(ops) if o[0] in('s','sdg','sx','sxdg')]; A=ops[:min(bidx)]
    ncz=sum(o[0]=='cz' for o in A); c=0
    for i,o in enumerate(A):
        if o[0]=='cz':
            c+=1
            if c==ncz//2: cut=i+1; break
    # include trailing 1q gates on qubits with no later cz in first half: approximate via wires
    w1=wires(A[:cut]); w2=wires(A[cut:])
    # compare cz-partner sequences only (order of edge colors)
    same=rev=0
    for q in w1:
        s1=[x[2] for x in w1[q] if x[0]=='cz']; s2=[x[2] for x in w2[q] if x[0]=='cz']
        same+= s1==s2; rev+= s1==s2[::-1]
    print(p.split('/')[-1],'qubits',len(w1),'cz-partner seq: 2nd half == 1st half (same order):',same,' == reversed:',rev)
