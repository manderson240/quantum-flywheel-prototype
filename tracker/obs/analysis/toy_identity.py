"""Toy check (6 qubits, dense): circuit A, then V, then A^-1 on |z>, measure O (diagonal),
parity-weighted average over all z  ==  Tr(O_A V^dag O_A V)/2^n with O_A = A O A^dag."""
import numpy as np
rng=np.random.default_rng(1); n=6; d=2**n
X=np.array([[0,1],[1,0]]); Z=np.diag([1,-1]); I=np.eye(2)
def kron(ops):
    m=np.array([[1.0]])
    for o in ops: m=np.kron(m,o)
    return m
H=rng.normal(size=(d,d))+1j*rng.normal(size=(d,d)); H=H+H.conj().T
w,v=np.linalg.eigh(H); A=v@np.diag(np.exp(-1j*w))@v.conj().T
rx=lambda t: np.cos(t/2)*I-1j*np.sin(t/2)*X
V=kron([rx(0.6) if q in (2,3,4) else I for q in range(n)])
O=kron([Z if q in (0,1) else I for q in range(n)])
W=np.linalg.inv(A)@V@A          # A applied first
lhs=np.mean([O[z,z]*(W.conj().T@O@W)[z,z].real for z in range(d)])
OA=A@O@A.conj().T
rhs=(np.trace(OA@V.conj().T@OA@V)/d).real
print('parity-avg circuit f =',lhs,' Tr(O_A V+ O_A V)/2^n =',rhs,' diff',abs(lhs-rhs))
