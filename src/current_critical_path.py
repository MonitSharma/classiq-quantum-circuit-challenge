"""Record simple per-wire congestion for the current best candidates."""
import json
from pathlib import Path
from qiskit import qasm2

def measure(path):
    q=qasm2.loads(Path(path).read_text()); counts=[0]*q.num_qubits
    for inst in q.data:
        for bit in inst.qubits: counts[q.find_bit(bit).index]+=1
    return {"path":path,"depth":q.depth(),"cx":q.count_ops().get("cx",0),"width":q.num_qubits,
            "operations_touching_qubit":counts,"busiest_qubits":sorted(range(len(counts)),key=lambda i:counts[i],reverse=True)[:6]}
def main():
    result=[measure("artifacts/753/pair_boundary_753.qasm"),measure("artifacts/531/full_mux_531.qasm")]
    Path("artifacts/current_critical_path.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=="__main__":main()
