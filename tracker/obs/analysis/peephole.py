"""Peephole-cancel the forward block A (before V) using per-qubit stacks.
rz commutes through cz; same-axis rotations merge; cz pairs cancel when adjacent on both wires.
Also S/SX named gates mapped to rotations. Reports residual gate counts."""
import sys, math, collections
sys.path.insert(0,__file__.rsplit('/',1)[0]); from parse_ole import parse
from echo_check import INV
def norm(a): 
    a=(a+math.pi)%(2*math.pi)-math.pi; return 0.0 if abs(a)<1e-9 or abs(abs(a)-2*math.pi)<1e-9 else a
def reduce(ops):
    st=collections.defaultdict(list)  # per qubit list of node ids
    nodes={}; nid=0
    def top_nonrz(q):
        # index of top element skipping rz for cz-cancellation
        L=st[q]; i=len(L)-1
        while i>=0 and nodes[L[i]][0]=='rz': i-=1
        return i
    for g,a,q,s in ops:
        if g=='s': g,a='rz',math.pi/2
        if g=='sdg': g,a='rz',-math.pi/2
        if g=='sx': g,a='rx',math.pi/2
        if g=='sxdg': g,a='rx',-math.pi/2
        if g in('rx','rz'):
            x=q[0]; L=st[x]
            if L and nodes[L[-1]][0]==g:
                n=nodes[L[-1]]; na=norm(n[1]+a)
                if na==0.0: L.pop(); del nodes[n[3]]
                else: nodes[n[3]]=(g,na,q,n[3])
                continue
            nodes[nid]=(g,a,q,nid); L.append(nid); nid+=1
        elif g=='cz':
            x,y=q; ix,iy=top_nonrz(x),top_nonrz(y)
            if ix>=0 and iy>=0 and st[x][ix]==st[y][iy] and nodes[st[x][ix]][0]=='cz':
                k=st[x][ix]; st[x].pop(ix); st[y].pop(iy); del nodes[k]
                # merge rz neighbours that may now touch
                for w in (x,y):
                    L=st[w]; j=0
                    while j<len(L)-1:
                        a1,a2=nodes[L[j]],nodes[L[j+1]]
                        if a1[0]==a2[0] and a1[0] in('rx','rz'):
                            na=norm(a1[1]+a2[1]); del nodes[a2[3]]; L.pop(j+1)
                            if na==0.0: del nodes[a1[3]]; L.pop(j); j=max(j-1,0)
                            else: nodes[a1[3]]=(a1[0],na,a1[2],a1[3])
                        else: j+=1
                continue
            nodes[nid]=('cz',None,q,nid); st[x].append(nid); st[y].append(nid); nid+=1
    return nodes
for p in sys.argv[1:]:
    ops=parse(p); bidx=[i for i,o in enumerate(ops) if o[0] in INV]; A=ops[:min(bidx)]
    res=reduce(A); c=collections.Counter(n[0] for n in res.values())
    qs=sorted({x for n in res.values() for x in n[2]})
    print(p.split('/')[-1],'A gates',len(A),'-> residual',dict(c),'qubits touched',len(qs))
