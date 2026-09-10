"""Comparator-free six-shell oracle.

Structure: one y-lookup loads six shell/threshold features, an (x5 AND y5)
conditional reflection of x0..x4 aligns both disks onto the common centre 40
while leaving the square's x range untouched, one x-phase multiplexer applies
all six rank-one terms, and two pair terms supply the radius-7 and radius-8
shells that do not fit in six ancillas.  See docs/CURRENT_DESIGN.md.
"""
from full_mux import multiplexer
from search import *
from pair_search import pair_circuit

def iv(a,b): return truth(range(a,b+1))

# y features loaded into ancillas 12..17
B=[iv(11,27)|iv(35,47),
   iv(12,26)|iv(36,46),
   iv(13,25)|iv(37,45),
   iv(13,25)|iv(39,43),
   iv(29,53),
   iv(39,43)]
# x tables applied against the matching ancilla, in reflected coordinates
H=[iv(38,42),
   truth([36,37,43,44]),
   truth([35,45]),
   truth([34,46]),
   iv(2,26),
   iv(27,31)|iv(47,63)]
# leftover x values {0,1,32,33}: exactly the states with x1=x2=x3=x4=0
LEFT=((1<<64)-1)^functools.reduce(lambda a,b:a^b,H)
CORR=[(truth([33,47]),iv(15,23)),(truth([32,48]),iv(17,21))]

def build(seed=0):
 lookup=multiplexer(B,list(range(12,18)),list(range(6,12)),'y',seed)
 tau=QuantumCircuit(18)
 for k in range(5):tau.rccx(11,5,k)
 q=lookup.copy()
 q.compose(tau,inplace=True)
 q.compose(multiplexer(H,list(range(12,18)),list(range(6)),'z',seed+10000),inplace=True)
 # The six Rz(pi*H_i) tables partition x except on LEFT, where the accumulated
 # -i factor is missing; restore it so the leftover phase is global.
 q.x([1,2,3,4]);q.mcp(-np.pi/2,[1,2,3],4);q.x([1,2,3,4])
 q.compose(tau.inverse(),inplace=True)
 q.compose(lookup.inverse(),inplace=True)
 for x,y in CORR:q.compose(pair_circuit(x,y),inplace=True)
 return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)

if __name__=='__main__':
 import sys
 assert LEFT==truth([0,1,32,33]),LEFT
 best=10**9
 for seed in range(int(sys.argv[1]) if len(sys.argv)>1 else 8):
  q=build(seed)
  d=q.depth()
  print(seed,d,q.count_ops(),flush=True)
  if d<best:
   best=d;Path('artifacts/shell6.qasm').write_text(qasm2.dumps(q));Path('artifacts/shell6_seed.json').write_text(str(seed))
 print('best',best)
