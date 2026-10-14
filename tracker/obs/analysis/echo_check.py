"""Check echo structure: is the circuit W = A . V . A^-1, and is A = B2.B1 with B2 = B1^-1 (exact echo)?
Per-qubit wire sequences (gate, angle, cz-partner) decide DAG equality."""
import sys, math, collections
sys.path.insert(0,__file__.rsplit('/',1)[0]); from parse_ole import parse
INV={'s':'sdg','sdg':'s','sx':'sxdg','sxdg':'sx'}
def inv(o):
    g,a,q,s=o
    if g in INV: return (INV[g],a,q,s)
    if g in('rx','rz'): return (g,-a,q,s)
    return o
def wires(ops):
    w=collections.defaultdict(list)
    for g,a,q,s in ops:
        for i,x in enumerate(q):
            w[x].append((g, None if a is None else round(a,9), tuple(y for y in q if y!=x)))
    return w
def is_inverse(A,B):
    """True if B == A^-1 as circuits (compare wires of B with reversed inverted wires of A)."""
    wa=wires([inv(o) for o in reversed(A)]); wb=wires(B)
    bad=[q for q in set(wa)|set(wb) if wa[q]!=wb[q]]
    return bad
for p in sys.argv[1:]:
    ops=parse(p)
    # V block: rz with angle 0.3/0.6 (delta*2) sandwiched by basis changes
    vidx=[i for i,o in enumerate(ops) if o[0]=='rz' and abs(abs(o[1])-round(abs(o[1]),1))<1e-12 and abs(o[1]) in (0.3,0.6)]
    bidx=[i for i,o in enumerate(ops) if o[0] in INV]
    lo,hi=min(bidx),max(bidx)
    A=ops[:lo]; V=ops[lo:hi+1]; C=ops[hi+1:]
    P=sorted({ops[i][2][0] for i in vidx})
    print('==',p.split('/')[-1],'|A|',len(A),'|V|',len(V),'|C|',len(C),'P sites',len(P),P)
    print('  C == A^-1 ? bad wires:',len(is_inverse(A,C)))
    n=len([o for o in A if o[0]=='cz']); 
    # split A into halves by cz count
    cnt=0; cut=None
    for i,o in enumerate(A):
        if o[0]=='cz':
            cnt+=1
            if cnt==n//2: cut=i+1
    # extend cut to include trailing single-qubit gates until next cz on same qubits? use segment boundary instead
    segs=sorted({o[3] for o in A}); mid=segs[len(segs)//2]
    B1=[o for o in A if o[3]<mid]; B2=[o for o in A if o[3]>=mid]
    bad=is_inverse(B1,B2)
    print('  A split at segment',mid,'|B1|',len(B1),'|B2|',len(B2),'cz',sum(o[0]=="cz" for o in B1),sum(o[0]=="cz" for o in B2),'-> B2==B1^-1 bad wires:',len(bad), sorted(bad)[:20])
