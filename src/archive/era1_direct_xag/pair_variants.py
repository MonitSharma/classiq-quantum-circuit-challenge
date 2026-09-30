"""Enumerate a small diverse set of raw and lowered variants per pair term."""
import hashlib, json
from pathlib import Path
from qiskit import qasm2, transpile
from xag_phase import alternatives, make_one
from xag import make_graph, plan

def variants(x,y,limit=6):
    g,roots=make_graph([(x,y)]); root=roots[0]; rows=[]; seen=set()
    for forms in alternatives(g,root,maxf=5):
        try:path=plan(g,frozenset(),forms,max_states=10000)
        except ValueError:continue
        raw=make_one(g,forms,path)
        raw_sig=hashlib.sha256(qasm2.dumps(raw).encode()).hexdigest()
        if raw_sig in seen:continue
        seen.add(raw_sig)
        out=transpile(raw,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)
        rows.append({"raw":raw,"lowered":out,"forms":[sorted(f) for f in forms],"path":list(path),
                     "raw_signature":raw_sig,"depth":out.depth(),"cx":out.count_ops().get("cx",0)})
    rows.sort(key=lambda r:(r["depth"],r["cx"]))
    selected=[]
    # Keep the isolated best plus structurally distinct candidates near it,
    # then fill remaining slots by CX/depth diversity.
    for row in rows:
        if not selected or row["forms"] != selected[-1]["forms"]:
            selected.append(row)
        if len(selected)>=limit:break
    return selected

def main():
    terms=json.loads(Path("artifacts/pair_terms.json").read_text()); root=Path("artifacts/pair_variants"); root.mkdir(exist_ok=True)
    inventory=[]
    for i,(x,y) in enumerate(terms):
        selected=variants(x,y)
        row={"term":i,"variants":[]}
        for j,v in enumerate(selected):
            raw_path=root/f"term_{i}_v{j}_raw.qasm"; low_path=root/f"term_{i}_v{j}.qasm"
            raw_path.write_text(qasm2.dumps(v["raw"])); low_path.write_text(qasm2.dumps(v["lowered"]))
            row["variants"].append({"id":j,"raw_qasm":str(raw_path),"qasm":str(low_path),"forms":v["forms"],"path":v["path"],"depth":v["depth"],"cx":v["cx"],"sha256":hashlib.sha256(low_path.read_bytes()).hexdigest()})
        inventory.append(row)
    Path("artifacts/pair_variant_inventory.json").write_text(json.dumps(inventory,indent=2))
    print(json.dumps({"terms":len(inventory),"variants_per_term":[len(x["variants"]) for x in inventory],"best":[(x["variants"][0]["depth"],x["variants"][0]["cx"]) for x in inventory]},indent=2))
if __name__=="__main__":main()
