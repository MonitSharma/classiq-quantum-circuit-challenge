"""Joint phase placement and scheduling on a fixed CNOT parity network.

Within each diagonal/CNOT block, a rotation may be applied at any wire interval
carrying the same input parity. Non-diagonal gates separate blocks. CP-SAT
selects occurrences and layers; the objective is only complete native depth.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from ortools.sat.python import cp_model
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from post190_commuting_schedule import records, dependency_graph


def problem(q):
    ops = records(q)
    fixed, blocks, current = [], [], []
    original_fixed = {}
    for i, (name, ws, params) in enumerate(ops):
        if name == 'u3' and abs(math.sin(params[0]/2)) < 1e-12:
            current.append(('phase', i, ws, params[1]+params[2]))
        elif name == 'cx':
            original_fixed[i] = len(fixed)
            current.append(('cx', len(fixed), ws, None))
            fixed.append((name, ws, params))
        else:
            if current:
                blocks.append(current)
                current = []
            original_fixed[i] = len(fixed)
            fixed.append((name, ws, params))
    if current:
        blocks.append(current)
    next_touch = {}
    previous_touch = {}
    last = [None]*q.num_qubits
    for i, op in enumerate(fixed):
        for w in op[1]:
            previous_touch[i,w] = last[w]
            if last[w] is not None:
                next_touch[last[w],w] = i
            last[w] = i
    first_touch = [next((i for i, op in enumerate(fixed) if w in op[1]), None) for w in range(q.num_qubits)]
    phases = []
    original_before = []
    seen_fixed = [None]*q.num_qubits
    for i, op in enumerate(ops):
        original_before.append(seen_fixed.copy())
        if i in original_fixed:
            for w in op[1]:
                seen_fixed[w] = original_fixed[i]
    for block in blocks:
        # Recover the true fixed gates immediately before the block.
        first = block[0]
        if first[0] == 'phase':
            before = original_before[first[1]].copy()
        else:
            idx = first[1]
            before = [max((j for j in range(idx) if w in fixed[j][1]), default=None) for w in range(q.num_qubits)]
        basis = [1 << w for w in range(q.num_qubits)]
        targets, options = {}, {}
        def interval(w, end):
            key = basis[w]
            option = (w, before[w], end)
            options.setdefault(key, set()).add(option)
        for kind, i, ws, angle in block:
            if kind == 'phase':
                key = basis[ws[0]]
                targets[key] = targets.get(key, 0.)+angle
            else:
                a,b = ws
                interval(a,i)
                interval(b,i)
                basis[b] ^= basis[a]
                before[a] = before[b] = i
        for w in range(q.num_qubits):
            end = first_touch[w] if before[w] is None else next_touch.get((before[w],w))
            interval(w,end)
        for parity, angle in targets.items():
            angle = (angle+math.pi) % (2*math.pi)-math.pi
            if abs(angle)>1e-11:
                phases.append(dict(parity=parity,angle=angle,
                                   options=sorted(options[parity],key=lambda x: (x[0],-1 if x[1] is None else x[1],len(fixed) if x[2] is None else x[2]))))
    return fixed, phases


def optimize(q, seconds, ceiling, commuting=False):
    fixed, phases = problem(q)
    model = cp_model.CpModel()
    span = model.new_int_var(1,ceiling,'depth')
    ftimes = [model.new_int_var(0,ceiling-1,f'f{i}') for i in range(len(fixed))]
    per_wire = [[] for _ in range(q.num_qubits)]
    last = [None]*q.num_qubits
    for i, op in enumerate(fixed):
        model.add(ftimes[i]+1 <= span)
        interval = model.new_fixed_size_interval_var(ftimes[i],1,f'fi{i}')
        for w in op[1]:
            per_wire[w].append(interval)
            if last[w] is not None and not commuting:
                model.add(ftimes[i] >= ftimes[last[w]]+1)
            last[w] = i
    if commuting:
        skeleton = QuantumCircuit(q.num_qubits)
        for name,ws,params in fixed:
            if name=='cx':skeleton.cx(*ws)
            else:skeleton.append(U3Gate(*params),list(ws))
        _,successors,_ = dependency_graph(skeleton)
        for i, successors_i in enumerate(successors):
            for j in successors_i:
                model.add(ftimes[j] >= ftimes[i]+1)
        # Phase commutes with control-side CXs. Every target-side operation
        # on each side of an occurrence must remain on that side, even when
        # the CX gates commute mutually and change their relative order.
        changing = [[i for i,op in enumerate(fixed) if w in op[1] and
                     (op[0]!='cx' or op[1][1]==w)] for w in range(q.num_qubits)]
    ptimes, choices = [], []
    for i, phase in enumerate(phases):
        t = model.new_int_var(0,ceiling-1,f'p{i}')
        model.add(t+1 <= span)
        ptimes.append(t)
        bs = []
        for j,(w,prev,nxt) in enumerate(phase['options']):
            b = model.new_bool_var(f'b{i}_{j}')
            bs.append(b)
            interval = model.new_optional_fixed_size_interval_var(t,1,b,f'pi{i}_{j}')
            per_wire[w].append(interval)
            if commuting:
                for index in changing[w]:
                    if prev is not None and index <= prev:
                        model.add(t>=ftimes[index]+1).only_enforce_if(b)
                    elif nxt is not None and index >= nxt:
                        model.add(t+1<=ftimes[index]).only_enforce_if(b)
            else:
                if prev is not None:
                    model.add(t>=ftimes[prev]+1).only_enforce_if(b)
                if nxt is not None:
                    model.add(t+1<=ftimes[nxt]).only_enforce_if(b)
        model.add_exactly_one(bs)
        choices.append(bs)
    for intervals in per_wire:
        model.add_no_overlap(intervals)
    model.minimize(span)
    assert not model.validate(),model.validate()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 1857
    status = solver.solve(model)
    report = dict(status=solver.status_name(status),seconds=solver.wall_time,lower=solver.best_objective_bound,
                  fixed_gates=len(fixed),phase_gates=len(phases),
                  placement_options=sum(len(p['options']) for p in phases),ceiling=ceiling,
                  commuting_skeleton=commuting)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None,report
    layers = [[] for _ in range(solver.value(span))]
    for i,op in enumerate(fixed):
        layers[solver.value(ftimes[i])].append(op)
    placements = []
    for i, phase in enumerate(phases):
        j = next(j for j,b in enumerate(choices[i]) if solver.boolean_value(b))
        w,prev,nxt = phase['options'][j]
        t = solver.value(ptimes[i])
        layers[t].append(('u3',(w,),(0.,0.,phase['angle'])))
        placements.append(dict(parity=phase['parity'],angle=phase['angle'],wire=w,layer=t,prev=prev,next=nxt))
    result = QuantumCircuit(q.num_qubits,global_phase=q.global_phase)
    for layer in layers:
        for name,ws,params in layer:
            if name=='cx':result.cx(*ws)
            else:result.append(U3Gate(*params),list(ws))
    report.update(depth=result.depth(),cx=result.count_ops().get('cx',0),placements=placements)
    return result,report


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    source=qasm2.load(a.source)
    result,report=optimize(source,a.seconds,a.ceiling or source.depth(),a.commuting)
    report.update(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  scope='Variable phase occurrence inside diagonal blocks; skeleton ordering as indicated by commuting_skeleton')
    if result is not None:
        path=a.outdir/f'candidate_d{result.depth()}_cx{result.count_ops().get("cx",0)}.qasm'
        path.write_text(qasm2.dumps(result))
        report['path']=str(path)
    (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k!='placements'},flush=True)
    if result is not None:
        from exhaustive_verify import exhaustive
        exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=45)
    p.add_argument('--ceiling',type=int)
    p.add_argument('--commuting',action='store_true')
    run(p.parse_args())
