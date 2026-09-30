"""Exact local order search around the verified 756-depth pair architecture."""
import json, random
from pathlib import Path
from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit

START = [9, 7, 1, 2, 0, 6, 3, 8, 4, 5]

def compile_order(blocks, order):
    q = QuantumCircuit(18)
    for i in order: q.compose(blocks[i], inplace=True)
    out = transpile(q, basis_gates=["u3", "cx"], optimization_level=3,
                    qubits_initially_zero=False)
    return out

def neighbors(order):
    n = len(order)
    seen = set()
    def add(x):
        t = tuple(x)
        if t != tuple(order) and t not in seen:
            seen.add(t); yield list(t)
    for i in range(n):
        for j in range(i + 1, n): yield from add(order[:i]+[order[j]]+order[i+1:j]+[order[i]]+order[j+1:])
    for i in range(n):
        for j in range(n):
            if i == j: continue
            x = order[:]; v=x.pop(i); x.insert(j,v); yield from add(x)
    for i in range(n):
        for j in range(i + 2, n + 1): yield from add(order[:i]+list(reversed(order[i:j]))+order[j:])
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                x=order[:]; x[i],x[j],x[k]=x[j],x[k],x[i]; yield from add(x)

def main():
    terms=json.loads(Path("artifacts/pair_terms.json").read_text()); blocks=[pair_circuit(x,y) for x,y in terms]
    cache={}; evaluations=[]
    def measure(order):
        key=tuple(order)
        if key not in cache:
            out=compile_order(blocks,order); cache[key]=(out.depth(),out.count_ops().get("cx",0),out)
        d,c,_=cache[key]; evaluations.append({"order":list(order),"depth":d,"cx":c}); return cache[key]
    order=START[:]; best=measure(order)[:2]; centers=[{"order":order[:],"depth":best[0],"cx":best[1]}]
    while True:
        winner=None
        for candidate in neighbors(order):
            score=measure(candidate)[:2]
            if score < (winner[0] if winner else best): winner=(score,candidate)
        if winner is None or winner[0] >= best: break
        best,order=winner; centers.append({"order":order[:],"depth":best[0],"cx":best[1]})
    rng=random.Random(20260911)
    for _ in range(200):
        candidate=order[:]
        for _ in range(rng.randint(1,3)):
            i,j=rng.sample(range(10),2); candidate[i],candidate[j]=candidate[j],candidate[i]
        score=measure(candidate)[:2]
        if score < best: best,order=score,candidate; centers.append({"order":order[:],"depth":best[0],"cx":best[1]})
    out=cache[tuple(order)][2]
    Path("artifacts/pair_756_local_order_search.json").write_text(json.dumps({"start":START,"best":{"order":order,"depth":best[0],"cx":best[1]},"centers":centers,"evaluated":len(cache),"results":evaluations},indent=2))
    Path("artifacts/pair_756_local_best.qasm").write_text(qasm2.dumps(out))
    print(json.dumps({"best":{"order":order,"depth":best[0],"cx":best[1]},"evaluated":len(cache)},indent=2))
if __name__ == "__main__": main()
