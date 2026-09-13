"""Bounded exact-circuit rewrites of the current relative-phase oracle."""
import json,signal,time
from pathlib import Path
from qiskit import qasm2
from distributed_frame_search import native
from pytket.qasm import circuit_from_qasm,circuit_to_qasm
from pytket import passes
import pyzx as zx

def timeout(*args):raise TimeoutError('60 second rewrite limit')
signal.signal(signal.SIGALRM,timeout)
out=Path('artifacts/post221_global_rewrites_v1');assert not out.exists();out.mkdir()
source=Path('artifacts/221/two_stage_221.qasm');rows=[]
for method in ['FullPeepholeOptimise','CliffordSimp','OptimisePhaseGadgets','PauliSimp','GreedyPauliSimp','teleport','zx_full']:
 start=time.monotonic();row=dict(method=method)
 try:
  signal.alarm(60)
  if method.startswith('zx') or method=='teleport':
   c=zx.Circuit.from_qasm(source.read_text());g=c.to_graph()
   if method=='teleport':g=zx.teleport_reduce(g);c=zx.Circuit.from_graph(g)
   else:zx.full_reduce(g);c=zx.extract_circuit(g)
   q=native(qasm2.loads(c.to_qasm()))
  else:
   c=circuit_from_qasm(str(source));getattr(passes,method)().apply(c)
   p=out/f'{method}_intermediate.qasm';circuit_to_qasm(c,str(p));q=native(qasm2.load(p,custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS))
  path=out/f'{method}_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q));row.update(depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path))
  if q.depth()<221:
   from exhaustive_verify import exhaustive
   exhaustive(path)
 except Exception as e:row.update(error=repr(e))
 finally:signal.alarm(0)
 row['seconds']=time.monotonic()-start;rows.append(row);print(row,flush=True);(out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
