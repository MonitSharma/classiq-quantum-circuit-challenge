"""Async loader/kernel-interface and dirty-assisted-kernel audit (corrected).

Measurements on the protected 185 architecture:

1.  Availability profile — when each of the eight kernel inputs (two raw
    parities plus six loaded label bits) becomes valid in the loader, and when
    the kernel first/last reads each input.  Semantic availability is measured
    (all 64 addresses), not merely last-touch.

2.  Dirty-assisted kernel — the recorded 38-layer eight-wire kernel embeds
    trivially on 18 wires (identity on the ten dirty wires), so ``D_dirty <=
    38`` at every width.  A bounded from-scratch ``psynth`` re-synthesis does
    not match that incumbent (it reaches ~45-52 at width 8), so it cannot close
    dirty-assisted synthesis; a bounded dirty-mediated-CNOT search *around* the
    incumbent is also run.

See ``docs/POST185_ASYNC_AND_DIRTY_KERNEL.md`` for the interpretation.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.quantum_info import Statevector

from distributed_ucry import structured_ucry
from post218_beam_phase import psynth
from post258_raw_parity_codes import cells
from post258_two_stage_anf import decode
import two_stage_oracle as ts


def kernel_inputs_profile(kernel_qasm):
    q = qasm2.load(kernel_qasm)
    n = q.num_qubits
    arrival = [0] * n
    first = [None] * n
    last = [0] * n
    for inst in q.data:
        ws = [q.find_bit(v).index for v in inst.qubits]
        t = max(arrival[w] for w in ws) + 1
        for w in ws:
            if first[w] is None:
                first[w] = t
            last[w] = t
            arrival[w] = t
    return dict(depth=q.depth(), cx=q.count_ops().get('cx', 0),
                first_use=first, last_use=last)


def loader_profile(lab, cls, mask, outwires, addr):
    cc = cells(cls, mask)
    codes = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
    tab = np.array([[math.pi * (code >> b & 1) for code in codes] for b in range(3)])
    best = None
    for seed in range(4):
        q = structured_ucry(tab, outwires, addr, seed, sparse=False, open_walk=True)
        nat = transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                        optimization_level=3, seed_transpiler=0)
        if best is None or nat.depth() < best.depth():
            best = nat
    arrival = [0] * best.num_qubits
    out_last = {}
    for inst in best.data:
        ws = [best.find_bit(v).index for v in inst.qubits]
        t = max(arrival[w] for w in ws) + 1
        for w in ws:
            arrival[w] = t
            if w in outwires:
                out_last[w] = t
    return dict(depth=best.depth(), cx=best.count_ops().get('cx', 0),
                output_last_touch=out_last)


def kernel_bit_dependency(kernel_recipe):
    co = np.array(kernel_recipe['co'])
    masks = [m for m in range(1, 256) if abs(co[m]) > 1e-12]
    from collections import Counter
    by_highest = Counter()
    for m in masks:
        by_highest[max(i for i in range(8) if m >> i & 1)] += 1
    cumulative, acc = {}, 0
    for k in range(8):
        acc += by_highest.get(k, 0)
        cumulative[k] = acc
    raw_only = [m for m in masks if (m & ~(1 | 16)) == 0]
    return dict(masks=len(masks), raw_only_masks=len(raw_only),
                by_highest_needed_bit=dict(sorted(by_highest.items())),
                cumulative_after_bit=cumulative)


def dirty_kernel_sweep(kernel_recipe, widths=(8, 10, 12, 14, 16, 18), seeds=6):
    co = np.array(kernel_recipe['co'])
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    rows = []
    for n in widths:
        best = None
        for seed in range(seeds):
            try:
                q = psynth(n, dict(targets), seed=seed, beam=24, branch=8, alpha=4.0)
                nat = transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                                optimization_level=3, seed_transpiler=0)
                score = (nat.depth(), nat.count_ops().get('cx', 0))
                if best is None or score[0] < best[0][0]:
                    best = score
            except Exception:
                pass
        rows.append(dict(width=n, dirty_wires=n - 8, depth=best[0], cx=best[1]))
    return rows


def kernel_embedding_depth(kernel_qasm='artifacts/185/kernel.qasm'):
    """The recorded 8-wire kernel placed on 18 wires (identity on the 10 dirty)."""
    from distributed_frame_search import native
    k = qasm2.load(kernel_qasm)
    kernel_wires = [11, 12, 13, 14, 4, 15, 16, 17]
    big = QuantumCircuit(18)
    for inst in k.data:
        ws = [kernel_wires[k.find_bit(v).index] for v in inst.qubits]
        big.append(inst.operation, ws)
    nat = native(big)
    return dict(kernel_depth=k.depth(), embedded_depth=nat.depth(),
                cx=nat.count_ops().get('cx', 0))


def dirty_mediation_search(kernel_qasm='artifacts/185/kernel.qasm'):
    """Bounded dirty-mediated-CNOT search around the recorded 38-layer kernel.

    Replaces, one at a time, a CX on the busiest kernel wire by the exact
    four-CX mediation CX(a,k),CX(k,b),CX(a,k),CX(k,b) through each dirty wire
    k, and records whether any lowers the native depth below the incumbent.
    """
    from distributed_frame_search import native
    k = qasm2.load(kernel_qasm)
    kernel_wires = [11, 12, 13, 14, 4, 15, 16, 17]
    dirty = [w for w in range(18) if w not in kernel_wires]
    big = QuantumCircuit(18)
    for inst in k.data:
        ws = [kernel_wires[k.find_bit(v).index] for v in inst.qubits]
        big.append(inst.operation, ws)
    baseline = native(big).depth()
    cx_idx = [i for i, inst in enumerate(big.data) if inst.operation.name == 'cx']
    from collections import Counter
    touches = Counter()
    for i in cx_idx:
        for w in [big.find_bit(v).index for v in big.data[i].qubits]:
            touches[w] += 1
    busy = touches.most_common(1)[0][0]
    targets = [i for i in cx_idx
               if busy in [big.find_bit(v).index for v in big.data[i].qubits]]
    best, tried = baseline, 0
    for i in targets:
        for med in dirty:
            a, b = [big.find_bit(v).index for v in big.data[i].qubits]
            q = QuantumCircuit(18)
            for j, g in enumerate(big.data):
                if j == i:
                    q.cx(a, med); q.cx(med, b); q.cx(a, med); q.cx(med, b)
                else:
                    q.append(g.operation, [q.find_bit(v).index for v in g.qubits])
            d = native(q).depth()
            tried += 1
            best = min(best, d)
    return dict(baseline_depth=baseline, mediations_tried=tried, best_depth=best)


def semantic_availability(lab, cls, mask, outwires, addr):
    """Earliest layer at which each loader output is semantically the final
    label for all 64 addresses (definite computational state, not last-touch).

    ``outwires`` here are 0-based positions within the 9-wire loader (address
    ``addr`` are 0..5, outputs are 6,7,8); returns the layer index per output,
    or None when it never becomes valid before the final gate.
    """
    cc = cells(cls, mask)
    codes = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
    tab = np.array([[math.pi * (code >> b & 1) for code in codes] for b in range(3)])
    q = structured_ucry(tab, outwires, addr, 0, sparse=False, open_walk=True)
    n = q.num_qubits
    result = {}
    for b in range(3):
        avail = None
        for L in range(len(q.data) + 1):
            prefix = QuantumCircuit(n)
            for inst in q.data[:L]:
                prefix.append(inst.operation, [prefix.find_bit(v).index for v in inst.qubits])
            ok = True
            for a in range(64):
                sv = Statevector.from_int(a, 2 ** n).evolve(prefix).data
                want = (codes[a] >> b) & 1
                target = a | (want << (6 + b))
                if abs(abs(sv[target])) < 1 - 1e-9:
                    ok = False
                    break
            if ok:
                avail = L
                break
        result[b] = avail
    return result


def run(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    cc = json.loads((Path('artifacts/185/class_codes.json')).read_text())
    yl = decode(cc['ylab']); xl = decode(cc['xlab'])

    kernel = kernel_inputs_profile('artifacts/185/kernel.qasm')
    yloader = loader_profile(yl, ts.ROWCLS, 32, [12, 13, 14], list(range(6)))
    xloader = loader_profile(xl, ts.COLCLS, 48, [15, 16, 17], list(range(6)))
    ysem = semantic_availability(yl, ts.ROWCLS, 32, [6, 7, 8], list(range(6)))

    recipe = json.loads(Path('artifacts/193/kernel_recipe.json').read_text())
    deps = kernel_bit_dependency(recipe)
    sweep = dirty_kernel_sweep(recipe)
    embedding = kernel_embedding_depth('artifacts/185/kernel.qasm')
    mediation = dirty_mediation_search('artifacts/185/kernel.qasm')

    report = dict(kernel=kernel, y_loader=yloader, x_loader=xloader,
                  y_loader_semantic_availability=ysem,
                  kernel_bit_dependency=deps, dirty_kernel_sweep=sweep,
                  kernel_embedding_18w=embedding,
                  dirty_mediation_search=mediation)
    (outdir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    run(p.parse_args().outdir)
