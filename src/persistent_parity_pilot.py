"""Measure affine-frame transition opportunities along four pair pebble paths.

This is a diagnostic, not a complete nonlinear compiler: RCCX changes the
semantic signal basis, so the report explicitly separates linear-frame savings
from a valid end-to-end oracle candidate.
"""
import json
from pathlib import Path
from qiskit import QuantumCircuit, transpile
from pair_search import pair_circuit
from xag import make_graph, linear
from persistent_parity import identity_frame, frame_from_linear_circuit, synthesize_transition, verify_transition

def main():
    terms=json.loads(Path("artifacts/pair_terms.json").read_text()); inventory=json.loads(Path("artifacts/pair_variant_inventory.json").read_text()); result={}
    for index in (5,9,4,2):
        x,y=terms[index]; g,roots=make_graph([(x,y)]); entry=inventory[index]["variants"][0]
        path=entry["path"]; q=QuantumCircuit(18); wire={v:v for v in range(12)}; live=set(); free=list(range(12,18)); frames=[]; old_cx=0; old_depth=0
        for v in path:
            a,b=g.nodes[v]; pre,p,r=linear(q,a,b,wire); frames.append(frame_from_linear_circuit(pre)); old_cx += 2*pre.count_ops().get("cx",0); old_depth += 2*pre.depth()
            if v in live:
                target=wire.pop(v); live.remove(v); free.append(target); free.sort()
            else:
                target=free.pop(0); wire[v]=target; live.add(v)
        transitions=[]; source=identity_frame()
        for target in frames:
            tr=synthesize_transition(source,target)
            transitions.append({"cx":tr.count_ops().get("cx",0),"depth":tr.depth()}); source=target
        final=synthesize_transition(source,identity_frame())
        result[str(index)]={"path_length":len(path),"old_prepare_restore_depth":old_depth,"old_prepare_restore_cx":old_cx,"transition_depth_sum":sum(t["depth"] for t in transitions)+final.depth(),"transition_cx_sum":sum(t["cx"] for t in transitions)+final.count_ops().get("cx",0),"transitions":transitions,"note":"linear-preparation diagnostic only; RCCX semantic basis changes are not yet integrated"}
    Path("artifacts/persistent_parity_pilot.json").write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=="__main__":main()
