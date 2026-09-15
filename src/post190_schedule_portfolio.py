"""Apply commuting-gate scheduling to distinct saved near-best full oracles."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from qiskit import qasm2
from distributed_frame_search import native
from post190_commuting_schedule import dependency_graph, reordered, schedule


def run(outdir, trials):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    # rg avoids walking irrelevant build trees and reads only candidate paths.
    paths = subprocess.check_output(['rg', '--files', 'artifacts'], text=True).splitlines()
    paths = [Path(p) for p in paths if re.search(r'(?:d19[0-6]_cx\d+|two_stage_19[0-6])\.qasm$', p)
             and 'kernel' not in p]
    seen, rows = set(), []
    for path in sorted(paths):
        text = path.read_text()
        sha = hashlib.sha256(text.encode()).hexdigest()
        if sha in seen:
            continue
        seen.add(sha)
        q = qasm2.loads(text)
        if q.num_qubits != 18:
            continue
        ops, succ, pred = dependency_graph(q)
        best = None
        best_seed = None
        for seed in range(trials):
            layers = schedule(ops, succ, pred, seed)
            if best is None or len(layers) < len(best):
                best = layers
                best_seed = seed
        candidate = native(reordered(q, best, pred))
        score = (candidate.depth(), candidate.count_ops().get('cx', 0))
        row = dict(source=str(path), source_sha256=sha, original_depth=q.depth(),
                   depth=score[0], cx=score[1], trials=trials, best_seed=best_seed,
                   order=[i for layer in best for i in layer],
                   u3=candidate.count_ops().get('u3', 0))
        if score < (189, 857):
            target = outdir / f'candidate{len(rows)}_d{score[0]}_cx{score[1]}.qasm'
            target.write_text(qasm2.dumps(candidate))
            row['path'] = str(target)
            from exhaustive_verify import exhaustive
            exhaustive(target)
        rows.append(row)
        print({k:v for k,v in row.items() if k!='order'}, flush=True)
        (outdir/'report.json').write_text(json.dumps(rows, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--trials', type=int, default=48)
    a = p.parse_args()
    run(a.outdir, a.trials)
