"""Test CNOT interaction rewrites directly against a strict depth target."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

from qiskit import qasm2
from post185_depth_walk import profile, moves_for
from post186_cnot_bridge import optimized_move
from post185_solver_walk import bounded_schedule


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    _, critical = profile(q)
    moves, _ = moves_for(q, critical)
    random.Random(a.seed).shuffle(moves)
    rows, history = [], []
    seen = set()
    started = time.monotonic()
    target = q.depth()-1
    for index, move in enumerate(moves[:a.trials]):
        if time.monotonic()-started >= a.seconds:
            break
        candidate, seed = optimized_move(q, *move, 2)
        text = qasm2.dumps(candidate)
        sha = hashlib.sha256(text.encode()).hexdigest()
        if sha in seen:
            continue
        seen.add(sha)
        result, solver = bounded_schedule(candidate, target, a.solve_seconds, a.seed+index)
        row = dict(index=index, move=move, shuffle_seed=seed, candidate_depth=candidate.depth(),
                   candidate_cx=candidate.count_ops().get('cx',0), source_sha256=sha, solver=solver)
        if result is not None:
            inp = a.outdir/f'input{index}.qasm'
            inp.write_text(text)
            path = a.outdir/f'candidate{index}_d{result.depth()}_cx{result.count_ops().get("cx",0)}.qasm'
            path.write_text(qasm2.dumps(result))
            from exhaustive_verify import exhaustive
            exhaustive(path)
            row.update(input_path=str(inp),path=str(path),depth=result.depth())
            history.append(row.copy())
            target = result.depth()-1
            print('DEPTH IMPROVEMENT', result.depth(), result.count_ops().get('cx',0), flush=True)
        rows.append(row)
        if len(rows)%10==0:
            print('strict depth', target, 'tested',len(rows),'last',solver['status'],flush=True)
        report = dict(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                      objective='Strict depth reduction; no CX objective or cap',available_moves=len(moves),
                      tested=len(rows),seconds=time.monotonic()-started,history=history,rows=rows)
        (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--trials',type=int,default=180)
    p.add_argument('--seconds',type=float,default=200)
    p.add_argument('--solve-seconds',type=float,default=3)
    p.add_argument('--seed',type=int,default=1855)
    run(p.parse_args())
