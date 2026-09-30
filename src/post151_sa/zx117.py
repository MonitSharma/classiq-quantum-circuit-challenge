"""ZX phase teleportation probe, with explicit wire identity on serialization."""
import json,time
from pathlib import Path
import pyzx as zx
from qiskit import qasm2,transpile
from postopt import parse_ops,fuse,write,depth
from canc import simplify
from smilp import solve
out=Path('artifacts/rewrite117_20260922/zx');out.mkdir(exist_ok=True);src=Path('artifacts/117/conditional_loader_117_cx577.qasm');q=qasm2.load(src)
z=transpile(q,basis_gates=['cx','rz','rx','h'],optimization_level=0,qubits_initially_zero=False);assert z.layout is None
c=zx.Circuit.from_qasm(qasm2.dumps(z));t=time.monotonic();g=zx.teleport_reduce(c.to_graph());d=zx.Circuit.from_graph(g);dq=qasm2.loads(d.to_qasm());n=transpile(dq,basis_gates=['u3','cx'],optimization_level=1,qubits_initially_zero=False);assert n.layout is None
p=out/'teleport.qasm';p.write_text(qasm2.dumps(n));ops=fuse(simplify(fuse(parse_ops(p)),False));write(ops,p);print('teleport',depth(ops),sum(o[0]=='cx' for o in ops),time.monotonic()-t,flush=True)
r=solve(ops,116,30);print('116',r is not None,flush=True)
if r is not None:write(fuse(r),out/'teleport_116.qasm')
