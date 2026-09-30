"""Joint local search over pair variants and term order."""
import json
from pathlib import Path
from qiskit import QuantumCircuit, transpile

START_ORDER=[9,7,1,2,5,4,8,0,6,3]
def compile_choice(choices,order):
    q=QuantumCircuit(18)
    for i in order:q.compose(choices[i],inplace=True)
    return transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
def main():
    inv=json.loads(Path("artifacts/pair_variant_inventory.json").read_text())
    variants=[[QuantumCircuit.from_qasm_file(v["qasm"]) for v in row["variants"]] for row in inv]
    choice=[0]*10; order=START_ORDER[:]; cache={}
    def measure(ch,o):
        key=(tuple(ch),tuple(o))
        if key not in cache:
            q=compile_choice([variants[i][ch[i]] for i in range(10)],o)
            cache[key]=(q.depth(),q.count_ops().get("cx",0),q)
        return cache[key]
    best=measure(choice,order)[:2]; accepted=[]
    changed=True
    while changed:
        changed=False
        # Variant coordinate descent at fixed order.
        for i in range(10):
            winner=(best,choice[i])
            for v in range(len(variants[i])):
                if v==choice[i]:continue
                trial=choice[:];trial[i]=v;s=measure(trial,order)[:2]
                if s<winner[0]:winner=(s,v)
            if winner[0]<best: choice[i]=winner[1];best=winner[0];accepted.append({"move":"variant","term":i,"variant":choice[i],"order":order[:],"depth":best[0],"cx":best[1]});changed=True
        # Exact order neighborhood with current variants.
        candidates=[]
        for i in range(10):
            for j in range(i+1,10):
                x=order[:];x[i],x[j]=x[j],x[i];candidates.append(x)
        for i in range(10):
            for j in range(10):
                if i!=j:x=order[:];v=x.pop(i);x.insert(j,v);candidates.append(x)
        for x in candidates:
            s=measure(choice,x)[:2]
            if s<best:best,order=s,x;accepted.append({"move":"order","order":order[:],"variants":choice[:],"depth":best[0],"cx":best[1]});changed=True
    q=measure(choice,order)[2]
    Path("artifacts/pair_variant_dp_search.json").write_text(json.dumps({"best":{"order":order,"variants":choice,"depth":best[0],"cx":best[1]},"accepted":accepted,"evaluated":len(cache)},indent=2))
    from qiskit import qasm2
    Path("artifacts/pair_variant_joint_best.qasm").write_text(qasm2.dumps(q))
    print(json.dumps({"best":{"order":order,"variants":choice,"depth":best[0],"cx":best[1]},"evaluated":len(cache)},indent=2))
if __name__=="__main__":main()
