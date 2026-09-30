"""Measure triple context around the current best pair order."""
import json
from pathlib import Path
from qiskit import QuantumCircuit, transpile
from pair_search import pair_circuit

START=[9,7,1,2,5,4,8,0,6,3]
def compile_blocks(blocks, order):
    q=QuantumCircuit(18)
    for i in order:q.compose(blocks[i],inplace=True)
    out=transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
    return out
def main():
    terms=json.loads(Path("artifacts/pair_terms.json").read_text()); blocks=[pair_circuit(x,y) for x,y in terms]
    pair={}; triples=[]
    for i in range(10):
        for j in range(10):
            if i!=j:
                out=compile_blocks(blocks,[i,j]); pair[i,j]=(out.depth(),out.count_ops().get("cx",0))
    for i in range(10):
        for j in range(10):
            if i==j:continue
            for k in range(10):
                if k in (i,j):continue
                out=compile_blocks(blocks,[i,j,k]); d=out.depth(); c=out.count_ops().get("cx",0)
                triples.append({"triple":[i,j,k],"depth":d,"cx":c,"marginal_depth":d-pair[i,j][0],"marginal_cx":c-pair[i,j][1]})
    # Greedy second-order rollout from the verified 753 order.
    order=START[:2]
    while len(order)<10:
        remaining=[x for x in range(10) if x not in order]
        pick=min(remaining,key=lambda k:next(t for t in triples if t["triple"]==[order[-2],order[-1],k])["marginal_depth"])
        order.append(pick)
    out=compile_blocks(blocks,order)
    best=min(triples,key=lambda x:(x["marginal_depth"],x["marginal_cx"]))
    payload={"start":START,"greedy_order":order,"greedy_score":{"depth":out.depth(),"cx":out.count_ops().get("cx",0)},"best_local_marginal":best,"triples":triples}
    Path("artifacts/pair_triple_boundary_search.json").write_text(json.dumps(payload,indent=2))
    print(json.dumps({k:payload[k] for k in ("greedy_order","greedy_score","best_local_marginal")},indent=2))
if __name__=="__main__":main()
