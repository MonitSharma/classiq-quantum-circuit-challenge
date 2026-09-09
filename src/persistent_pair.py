"""End-to-end semantic-frame pair compiler for an existing XAG pebble path."""
from pathlib import Path
import json
from qiskit import QuantumCircuit, qasm2, transpile
from xag import make_graph, linear
from xag import phase_forms
from semantic_frame import FULL, synthesize_transition, apply_circuit, rank

INPUT_TT=[sum(1<<i for i in range(4096) if i>>b&1) for b in range(12)]

def form_tt(g, form):
    value=0
    for v in form:value ^= FULL if v==-1 else g.tt[v]
    return value

def target_rows(current, desired, positions):
    rows=[None]*18
    source_rank=qrank(current)
    for index,value in enumerate(desired):
        if qrank(current+[value])!=source_rank:
            raise ValueError(f"desired semantic value outside current frame span index={index}")
    used=set(positions)
    for p,value in zip(positions,desired):rows[p]=value
    basis=[]; current_rank=source_rank; selected=[value for value in rows if value is not None]
    for value in current:
        if qrank(selected+[value])>qrank(selected):basis.append(value);selected.append(value)
    for i in range(18):
        if rows[i] is None and basis:
            rows[i]=basis.pop(0)
    for i in range(18):
        if rows[i] is None:rows[i]=0
    if qrank(rows)!=current_rank:raise ValueError("target frame lost semantic span")
    target_rank=qrank(rows)
    for value in current:
        if qrank(rows+[value])!=target_rank:
            raise ValueError("target frame changed semantic span")
    return rows

def contains(rows, value):
    return qcontains(rows,value)

def qvalue(value):
    return value ^ FULL if (value >> 4095)&1 else value

def qrank(values):
    return rank([qvalue(v) for v in values])

def qcontains(rows,value):
    r=qrank(rows); return qrank(list(rows)+[value])==r

def same_span(a,b):
    ra=qrank(a); rb=qrank(b)
    return ra==rb and all(contains(b,v) for v in a) and all(contains(a,v) for v in b)

def compile_pair(x,y,forms,path):
    g,roots=make_graph([(x,y)]); q=QuantumCircuit(18); compute=QuantumCircuit(18)
    current=[*INPUT_TT,*([0]*6)]; wire={v:v for v in range(12)}; live=set(); free=list(range(12,18))
    for step,node in enumerate(path):
        base_rank=qrank(current)
        missing_inputs=[i for i,v in enumerate(INPUT_TT) if qrank(current+[v])!=base_rank]
        missing_live=[n for n in live if qrank(current+[g.tt[n]])!=base_rank]
        if missing_inputs or missing_live: raise ValueError(f"semantic span lost before step {step} node {node}: inputs={missing_inputs} live={missing_live}")
        a,b=g.nodes[node]; at,bt=form_tt(g,a),form_tt(g,b)
        if node in live: target=wire[node]; target_value=g.tt[node]
        else: target=free.pop(0); target_value=0
        # Keep every live nonlinear signal on its assigned wire.  Only unused
        # wires are eligible as temporary parity pivots, so later uncomputes
        # retain their semantic targets.
        best=None; last_error=None
        protected_slots={wire[n] for n in live}
        for p in range(18):
            if p==target or p in protected_slots:continue
            for r in range(18):
                if r in (p,target) or r in protected_slots:continue
                try:
                    fixed={p:at,r:bt,target:target_value}
                    for live_node in live:
                        if live_node!=node: fixed[wire[live_node]]=g.tt[live_node]
                    desired=target_rows(current,list(fixed.values()),list(fixed.keys()))
                    post=desired[:]; post[target]=target_value ^ (at&bt)
                    after_live=set(live)
                    if node in after_live:after_live.remove(node)
                    else:after_live.add(node)
                    expected_post=INPUT_TT+[g.tt[n] for n in sorted(after_live)]+[0]*(6-len(after_live))
                    if not same_span(post,expected_post): raise ValueError("post-toggle semantic span not preserved")
                    tr=synthesize_transition(current,desired); score=(tr.depth(),tr.count_ops().get("cx",0))
                except ValueError as error: last_error=error; continue
                if best is None or score<best[0]:best=(score,p,r,desired,tr)
        if node in live: best=None
        if best is None:
            # Safe fallback: restore a canonical semantic frame, then use the
            # trusted prepare/RCCX/restore toggle for this constrained step.
            canonical_wire={v:v for v in range(12)}
            live_slots={live_node:12+i for i,live_node in enumerate(sorted(live))}
            canonical_wire.update(live_slots)
            fixed_values=INPUT_TT+[g.tt[n] for n in sorted(live)]+[0]*(6-len(live))
            fixed_positions=list(range(12))+list(live_slots.values())+[s for s in range(12,18) if s not in live_slots.values()]
            canonical=target_rows(current,fixed_values,fixed_positions)
            try: tr=synthesize_transition(current,canonical)
            except ValueError as error: raise ValueError(f"fallback frame at node {node}: {error}")
            q.compose(tr,inplace=True); compute.compose(tr,inplace=True); current=apply_circuit(current,tr); assert current==canonical, f"canonical frame transition failed at node {node}"; wire=canonical_wire
            free=[slot for slot in range(12,18) if slot not in wire.values()]
            if node in live: target=wire[node]
            else: target=free.pop(0)
            pre,p,r=linear(compute,a,b,wire); q.compose(pre,inplace=True);compute.compose(pre,inplace=True);current=apply_circuit(current,pre)
            q.rccx(p,r,target);compute.rccx(p,r,target);current[target]^=at&bt
            q.compose(pre.inverse(),inplace=True);compute.compose(pre.inverse(),inplace=True);current=apply_circuit(current,pre.inverse())
            expected=canonical[:]; expected[target]=0 if node in live else g.tt[node]
            assert current==expected, f"canonical fallback failed at node {node}"
            if node in live: live.remove(node);wire.pop(node);free.append(target);free.sort()
            else: live.add(node);wire[node]=target
            continue
        _,p,r,desired,tr=best; q.compose(tr,inplace=True); compute.compose(tr,inplace=True); current=apply_circuit(current,tr)
        assert current==desired, f"transition simulation mismatch node={node}"
        # The quotient-span test treats FULL as an affine offset, but RCCX
        # controls are ordinary Boolean truth tables.  Require the exact
        # requested control/target values before using the transition.
        if current[p] != at or current[r] != bt or current[target] != target_value:
            raise ValueError(
                f"transition chose affine-complemented control/target at step {step}: "
                f"p={p} r={r} target={target}"
            )
        # The transition may move live nonlinear signals. Rebind their wires
        # by exact semantic truth table before the next RCCX.
        rebound={}; used=set()
        for live_node in live:
            slot=wire[live_node]
            if current[slot]!=g.tt[live_node]:raise ValueError(f"live node {live_node} moved during frame transition")
            rebound[live_node]=slot;used.add(slot)
        wire.update(rebound)
        free=[slot for slot,value in enumerate(current) if value==0 and slot not in wire.values()]
        q.rccx(p,r,target); compute.rccx(p,r,target); current[target]^=at&bt
        assert current[target] == (g.tt[node] if node not in live else 0), f"toggle mismatch step={step} node={node} target={target} live={sorted(live)} actual={current[target]} expected={(g.tt[node] if node not in live else 0)} product={at&bt} target_value={target_value}"
        if node in live:
            live.remove(node); wire.pop(node); free.append(target); free.sort()
        else:
            live.add(node);wire[node]=target
            free=[slot for slot in free if slot != target]
        missing=[n for n in live if g.tt[n] not in current]
        if missing: raise ValueError(f"live semantic loss after step {step} node {node}: {missing}")
    canonical=[*INPUT_TT,*([0]*6)]
    for node,slot in wire.items():canonical[slot]=g.tt[node]
    print('final live',sorted(live),'qrank current/canonical',qrank(current),qrank(canonical),'same',same_span(current,canonical),flush=True)
    try: tr=synthesize_transition(current,canonical)
    except ValueError as error: raise ValueError(f"final frame: {error}")
    q.compose(tr,inplace=True);compute.compose(tr,inplace=True)
    selected_forms=tuple(frozenset(f) for f in forms)
    phase_forms(q, selected_forms[0], selected_forms[1], wire={v:v for v in range(12)}|{node:slot for node,slot in wire.items()})
    q.compose(compute.inverse(),inplace=True)
    return transpile(q,basis_gates=["u3","cx"],optimization_level=3,qubits_initially_zero=False)

def main():
    terms=json.loads(Path("artifacts/pair_terms.json").read_text()); inv=json.loads(Path("artifacts/pair_variant_inventory.json").read_text()); result={}
    for i in (5,9,4,2):
        x,y=terms[i]; entry=inv[i]["variants"][0]
        try:
            out=compile_pair(x,y,entry["forms"],entry["path"])
            path=f"artifacts/persistent_pair_{i}.qasm";Path(path).write_text(qasm2.dumps(out));result[str(i)]={"status":"candidate","depth":out.depth(),"cx":out.count_ops().get("cx",0),"width":out.num_qubits,"path":path}
        except Exception as error:
            result[str(i)]={"status":"infeasible_prototype","error":str(error)}
    Path("artifacts/persistent_pair_pilot.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=="__main__":main()
