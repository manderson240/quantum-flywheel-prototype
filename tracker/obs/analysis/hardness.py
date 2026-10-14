"""Cheap structural hardness indicators for OLE instances (no simulation).
- graph distances between observable sites O, perturbation sites P, scattering sites S
- peephole-reduced full circuit W = A.V.A^-1; backward causal cone of O through reduced W
- non-Clifford rotation count inside the cone (angles not multiple of pi/2)."""
import sys, math, collections
sys.path.insert(0,__file__.rsplit('/',1)[0])
from parse_ole import parse
import peephole
OBS={'49Q':[52,59,72],'70Q':[52,59,72],'56':[131,132,133,134,135,138,139,151,152,153,154,155]}
def bfs(adj,src):
    d={s:0 for s in src}; fr=list(src)
    while fr:
        nf=[]
        for u in fr:
            for v in adj[u]:
                if v not in d: d[v]=d[u]+1; nf.append(v)
        fr=nf
    return d
def noncliff(a): return a is not None and abs(a/(math.pi/2)-round(a/(math.pi/2)))>1e-6
for p in sys.argv[1:]:
    name=p.split('/')[-1]; O=OBS['56' if '56x' in name else name[:3]]
    ops=parse(p); used={q for o in ops for q in o[2]}
    adj=collections.defaultdict(set)
    for g,a,q,s in ops:
        if g=='cz': adj[q[0]].add(q[1]); adj[q[1]].add(q[0])
    bidx=[i for i,o in enumerate(ops) if o[0] in('s','sdg','sx','sxdg')]; A=ops[:min(bidx)]
    wA=collections.defaultdict(list)
    for g,a,q,s in A:
        for x in q: wA[x].append((g,None if a is None else round(a,6),tuple(y for y in q if y!=x)))
    S=[q for q,L in wA.items() if [(g,None if a is None else -a,pp) for g,a,pp in reversed(L)]!=L]
    P=sorted({o[2][0] for o in ops if o[0]=='rz' and o[1] is not None and abs(abs(o[1])-0.3)<1e-9 or (o[0]=='rz' and o[1] is not None and abs(abs(o[1])-0.6)<1e-9)})
    dO=bfs(adj,O); ecc=max(max(bfs(adj,[u]).values()) for u in used)
    print('==',name,'n',len(used),'diameter',ecc,'|O|',len(O),'|P|',len(P),'|S|',len(S),'O∩P',sorted(set(O)&set(P)),'O∩S',sorted(set(O)&set(S)))
    print('  dist(O->S) min',(min(dO[s] for s in S) if S else None),'dist(O->P) min',min(dO[x] for x in P), ' S sites',sorted(S))
    # reduced full circuit
    nodes=peephole.reduce(ops)
    order=sorted(nodes.values(), key=lambda n:n[3])
    cz=[n for n in order if n[0]=='cz']; rot=[n for n in order if n[0] in('rx','rz')]
    print('  reduced full W: cz',len(cz),'rot',len(rot),'nonClifford rot',sum(noncliff(n[1]) for n in rot))
    # backward causal cone from O (Heisenberg: O evolved by W^dag... cone = gates that can affect <O>)
    cone=set(O); ncone=0; ncz=0
    for n in reversed(order):
        q=n[2]
        if n[0]=='cz':
            if q[0] in cone or q[1] in cone: cone|=set(q); ncz+=1
        elif q[0] in cone and noncliff(n[1]): ncone+=1
    print('  O backward light cone: qubits',len(cone),'/',len(used),'cz in cone',ncz,'nonClifford rot in cone',ncone)
    # cone of O through reduced A only (the "scrambler" half: A O A^dag); A applied first
    nA=peephole.reduce(A); oA=sorted(nA.values(), key=lambda n:n[3])
    cone=set(O); ncone=0; ncz=0
    for n in reversed(oA):
        q=n[2]
        if n[0]=='cz':
            if q[0] in cone or q[1] in cone: cone|=set(q); ncz+=1
        elif q[0] in cone and noncliff(n[1]): ncone+=1
    print('  reduced A only: cz',sum(n[0]=="cz" for n in oA),'| O cone qubits',len(cone),'cz',ncz,'nonClifford',ncone, '| cone∩P',len(cone&set(P)))
