"""Joint output-frame and exact distributed-lookup selection, with replay data."""
import argparse
from collections import deque
import itertools
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
import distributed_ucry as d
import level_oracle as l
from level_encoder_search_fast import CODES


def frame_library():
    identity = (1, 2, 4)
    known = {identity: []}
    queue = deque([identity])
    while queue:
        rows = queue.popleft()
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                nxt = list(rows)
                nxt[b] ^= nxt[a]
                nxt = tuple(nxt)
                if nxt not in known:
                    known[nxt] = known[rows]+[(a, b)]
                    queue.append(nxt)
    assert len(known) == 168
    return known


FRAMES = frame_library()


def factored_base_kernel():
    """a*f XOR (a XOR f)*(b*d XOR c*e), in (a,b,c,d,e,f) order."""
    q = QuantumCircuit(6)
    q.cz(0, 5)
    q.cx(0, 5)
    q.ccz(5, 1, 3)
    q.ccz(5, 2, 4)
    q.cx(0, 5)
    return q


def frame_circuit(rows):
    q = QuantumCircuit(3)
    for a, b in FRAMES[tuple(rows)]:
        q.cx(a, b)
    return q


def transformed(triple, frame):
    return tuple(__import__('functools').reduce(int.__xor__,
                 (triple[b] for b in range(3) if row >> b & 1), 0) for row in frame)


def native(raw):
    compiled = transpile(raw, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                         optimization_level=3, seed_transpiler=0)
    return materialize_output_layout(compiled)


def materialize_output_layout(compiled):
    """Keep logical wire identities when serializing or composing a subcircuit.

    QASM2 and compose do not apply TranspileLayout. Elided permutations must
    therefore be restored as real gates, even with initially_zero=False.
    """
    n = compiled.num_qubits
    if compiled.layout is None:
        return compiled
    assert compiled.layout.initial_index_layout() == list(range(n)), \
        'Unexpected input placement; output-only correction is insufficient'
    positions = compiled.layout.final_index_layout()
    assert sorted(positions) == list(range(n))
    if positions == list(range(n)):
        return compiled
    out = QuantumCircuit(n)
    out.compose(compiled, inplace=True)
    contents = [positions.index(i) for i in range(n)]
    for logical in range(n):
        other = contents.index(logical)
        if other != logical:
            out.cx(logical, other)
            out.cx(other, logical)
            out.cx(logical, other)
            contents[logical], contents[other] = contents[other], contents[logical]
    assert contents == list(range(n))
    return out


def side_candidates(side, seeds, keep):
    original = CODES[0][side == 'v']
    # Each unordered basis is represented by its shortest physical CX frame.
    frames = [min(itertools.permutations(rows), key=lambda f: len(FRAMES[f]))
              for rows in itertools.combinations(range(1, 8), 3) if d.rank(rows) == 3]
    frames = sorted(set(frames), key=lambda f: len(FRAMES[f]))
    found = []
    for frame in frames:
        triple = transformed(original, frame)
        tabs = [np.array(l.angle_table(l.code_of(triple, l.LEVEL[side+str(p)])[1])) for p in (1, 2)]
        stages = []
        circuits = []
        for angles in (tabs[0], tabs[1]-tabs[0], -tabs[1]):
            shortlist = []
            for seed in range(seeds):
                for sparse, open_walk in [(False, True), (True, False)]:
                    raw = d.structured_ucry(angles, [6, 7, 8], list(range(6)), seed,
                                            sparse=sparse, open_walk=open_walk)
                    shortlist.append((raw.depth(), raw.size(), seed, sparse, open_walk, raw))
            shortlist.sort(key=lambda r: r[:2])
            best = None
            for _, _, seed, sparse, open_walk, raw in shortlist[:3]:
                q = native(raw)
                score = q.depth(), q.count_ops().get('cx', 0)
                if best is None or score < best[0]:
                    best = score, q, dict(seed=seed, sparse=sparse, open_walk=open_walk,
                                           depth=score[0], cx=score[1])
            stages.append(best[2])
            circuits.append(best[1])
        score = sum(c.depth() for c in circuits) + 4*len(FRAMES[frame])
        record = dict(frame=frame, triple=triple, stages=stages, proxy=score)
        found.append((score, record, circuits))
        print(side, record, flush=True)
    found.sort(key=lambda item: item[0])
    selected = found[:keep]
    identity = next(item for item in found if item[1]['frame'] == (1, 2, 4))
    if identity not in selected:
        selected.append(identity)
    return selected, [item[1] for item in found]


def kernel(yr, xr, base_kernel=None):
    q = QuantumCircuit(18)
    yframe, xframe = frame_circuit(yr['frame']), frame_circuit(xr['frame'])
    q.compose(yframe.inverse(), l.YA, inplace=True)
    q.compose(xframe.inverse(), l.XA, inplace=True)
    q.compose(factored_base_kernel() if base_kernel is None else base_kernel, l.YA+l.XA, inplace=True)
    q.compose(yframe, l.YA, inplace=True)
    q.compose(xframe, l.XA, inplace=True)
    conjugated = native(q)
    q = QuantumCircuit(18)
    a = l.code_of(yr['triple'], l.LEVEL['u1'])[0]
    b = l.code_of(xr['triple'], l.LEVEL['v1'])[0]
    l.emit_kernel(q, l.kernel_terms(a, b), l.YA, l.XA)
    direct = native(q)
    return min([conjugated, direct], key=lambda c: (c.depth(), c.count_ops().get('cx', 0)))


def run(outdir, seeds, keep):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    ys, yr = side_candidates('u', seeds, keep)
    (outdir/'y_candidates.json').write_text(json.dumps(yr, indent=2)+'\n')
    xs, xr = side_candidates('v', seeds, keep)
    (outdir/'x_candidates.json').write_text(json.dumps(xr, indent=2)+'\n')
    results = []
    best = None
    for (_, yrecord, ycircuits), (_, xrecord, xcircuits) in itertools.product(ys, xs):
        k = kernel(yrecord, xrecord)
        q = QuantumCircuit(18)
        for stage in range(3):
            q.compose(ycircuits[stage], l.YW+l.YA, inplace=True)
            q.compose(xcircuits[stage], l.XW+l.XA, inplace=True)
            if stage < 2:
                q.compose(k, inplace=True)
        q = native(q)
        record = dict(y=yrecord, x=xrecord, kernel_depth=k.depth(),
                      depth=q.depth(), cx=q.count_ops().get('cx', 0))
        results.append(record)
        score = q.depth(), q.count_ops().get('cx', 0)
        if best is None or score < best:
            best = score
            path = outdir/f'candidate{len(results)}_d{q.depth()}.qasm'
            path.write_text(qasm2.dumps(q))
            record['path'] = str(path)
            print('candidate', record, flush=True)
    (outdir/'report.json').write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seeds', type=int, default=12)
    p.add_argument('--keep', type=int, default=6)
    args = p.parse_args()
    run(args.outdir, args.seeds, args.keep)
