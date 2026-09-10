"""Test algebraic merges and boundary ordering for the repeated endpoint stars."""
import json, random
from pathlib import Path
from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit

def compile_blocks(blocks, order):
    q=QuantumCircuit(18)
    for i in order:q.compose(blocks[i],inplace=True)
    return transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)

def optimize(blocks):
    n=len(blocks); rng=random.Random(20260912); orders=[list(range(n)),list(reversed(range(n)))]
    orders += [rng.sample(range(n),n) for _ in range(100)]
    best=None;bestq=None;bo=None
    for order in orders:
        q=compile_blocks(blocks,order); s=(q.depth(),q.count_ops().get("cx",0))
        if best is None or s<best:best,bestq,bo=s,q,order
    return best,bestq,bo

def main():
    p=json.loads(Path("artifacts/global_12_edge_endpoints.json").read_text())
    edges=[(e["x_truth_table"],e["y_truth_table"]) for e in p["edges"]]
    cases={"none":edges}
    cases["x_star_merge"]=[(edges[0][0],edges[0][1]^edges[1][1])]+edges[2:]
    cases["y_star_merge"]=edges[:7]+[(edges[7][0]^edges[8][0],edges[7][1])]+edges[9:]
    cases["both_star_merge"]=[(edges[0][0],edges[0][1]^edges[1][1])]+edges[2:7]+[(edges[7][0]^edges[8][0],edges[7][1])]+edges[9:]
    result={}
    for name,terms in cases.items():
        blocks=[pair_circuit(x,y) for x,y in terms]; score,q,order=optimize(blocks)
        result[name]={"terms":terms,"order":order,"depth":score[0],"cx":score[1],"width":q.num_qubits}
        Path(f"artifacts/global_endpoint_star_{name}.qasm").write_text(qasm2.dumps(q))
    Path("artifacts/global_endpoint_star_metrics.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({k:{z:v[z] for z in ("depth","cx","width","order")} for k,v in result.items()},indent=2))
if __name__=="__main__":main()
