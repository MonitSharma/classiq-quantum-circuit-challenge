"""Compare global compilation of raw pair blocks versus lowered pair blocks."""
import json
from pathlib import Path
from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit
from xag_phase import alternatives, make_one
from xag import make_graph, plan
from formula import formula, remap

ORDER=[9,7,1,2,5,4,8,0,6,3]

def main():
    terms=json.loads(Path("artifacts/pair_terms.json").read_text()); raw=[]; lowered=[]
    for x,y in terms:
        g,roots=make_graph([(x,y)]); root=roots[0]; best=None; best_score=None
        for forms in alternatives(g,root,maxf=5):
            try:path=plan(g,frozenset(),forms,max_states=10000)
            except ValueError:continue
            q=make_one(g,forms,path)
            out=transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
            s=(out.depth(),out.count_ops().get("cx",0))
            if best is None or s<best_score:best,best_score=q,s
        raw.append(best); lowered.append(pair_circuit(x,y))
    result={}
    for mode,blocks in (("raw",raw),("pretranspiled",lowered)):
        q=QuantumCircuit(18)
        for i in ORDER:q.compose(blocks[i],inplace=True)
        out=transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
        result[mode]={"depth":out.depth(),"cx":out.count_ops().get("cx",0),"width":out.num_qubits}
        Path(f"artifacts/pair_{mode}_global.qasm").write_text(qasm2.dumps(out))
    Path("artifacts/pair_raw_global_comparison.json").write_text(json.dumps({"order":ORDER,"results":result},indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
