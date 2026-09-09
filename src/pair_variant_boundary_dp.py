"""K=4 variant boundary model and dynamic-programming shortlist."""
import json
from pathlib import Path
from qiskit import QuantumCircuit, transpile

def score(a,b):
    q=QuantumCircuit(18);q.compose(a,inplace=True);q.compose(b,inplace=True)
    o=transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
    return o.depth(),o.count_ops().get("cx",0)
def full(vs,order):
    q=QuantumCircuit(18)
    for i,v in order:q.compose(vs[i][v],inplace=True)
    return transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
def main():
    inv=json.loads(Path("artifacts/pair_variant_inventory.json").read_text()); vs=[[QuantumCircuit.from_qasm_file(v["qasm"]) for v in r["variants"][:4]] for r in inv]
    boundary={}
    for i in range(10):
        for j in range(10):
            if i==j:continue
            for a in range(len(vs[i])):
                for b in range(len(vs[j])):boundary[f"{i},{a},{j},{b}"]=score(vs[i][a],vs[j][b])
    # Keep the cheapest path for each (subset,last,variant), using boundary
    # depth as a shortlist proxy; actual full compilation follows.
    dp={(1<<i,i,v):(0,[(i,v)]) for i in range(10) for v in range(len(vs[i]))}
    for size in range(1,10):
        for (mask,last,v),(cost0,path) in list(dp.items()):
            if mask.bit_count()!=size:continue
            for j in range(10):
                if mask>>j&1:continue
                for b in range(len(vs[j])):
                    d,c=boundary[f"{last},{v},{j},{b}"]; key=(mask|1<<j,j,b); cand=(cost0+d,[*path,(j,b)])
                    if key not in dp or cand[0]<dp[key][0]:dp[key]=cand
    finals=sorted((x for (mask,_,_),x in dp.items() if mask==(1<<10)-1),key=lambda x:x[0])[:50]
    actual=[]
    for proxy,path in finals:
        o=full(vs,[*path]); actual.append({"proxy":proxy,"order":[i for i,v in path],"variants":[v for i,v in path],"depth":o.depth(),"cx":o.count_ops().get("cx",0)})
    best=min(actual,key=lambda x:(x["depth"],x["cx"]))
    Path("artifacts/pair_variant_boundary_costs.json").write_text(json.dumps(boundary,indent=2));Path("artifacts/pair_variant_dp_search.json").write_text(json.dumps({"best":best,"top_actual":actual,"states":len(dp),"variant_cap":4},indent=2));print(json.dumps({"states":len(dp),"best":best},indent=2))
if __name__=="__main__":main()
