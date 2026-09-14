"""Kernel endpoint search against the loaders the package actually ships.

`post193_endpoint_beam` scored candidate kernels against arrival times taken
from loader seeds 99 and 155, but the packaged 193/853 oracle uses seeds 298 and
506.  A kernel scheduled for the wrong arrival profile is being optimised against
the wrong critical path, so this recomputes arrival from the shipped loaders and
searches a finer configuration grid than the sixteen (alpha, timew) pairs the
earlier sweep cycled through.

The output contract is unchanged: the beam's completed linear state is finished
to an ancilla *permutation* rather than to the identity, and the permutation is
absorbed by rewiring the inverse loader, so it costs no gates.
"""
import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
from qiskit import qasm2

from build_two_stage_196 import encoders, KERNEL_WIRES
from distributed_frame_search import native
from post193_endpoint_beam import mapping_of
from post196_free_ancilla_order import finish
from post218_beam_phase import psynth
from post258_joint_encoder_schedule import touches

# The earlier sweep cycled only sixteen (alpha, timew) pairs at one beam size.
# `horizon` switches the beam ranking from "fewest parities left" to committed
# depth plus an optimistic remainder, and `fill` allows wider CX layers; neither
# had been combined with the relaxed endpoint contract.
# Focused on the region that produced 192: the A*-style ranking (`horizon`) with
# a strong time weight.  Every configuration that reached 194 or better in the
# wide sweep had horizon set, so the low-horizon half of the grid is dropped.
# The 191 configuration sat on the previous grid's boundary (timew 1.2,
# horizon 1.5), so the grid is pushed outward in both of those directions.
# Each winning configuration so far has sat on the previous grid's boundary
# (191 at timew 1.2 / horizon 1.5, then 190 at beam 128 / branch 22 /
# horizon 2.2 / fill 3), so the grid keeps being pushed in those directions.
# v6 pushed beams to 192, branch to 28 and horizon to 4.5 and stopped paying, so
# the grid is returned to the region that produced 191 and 190 and sampled harder.
GRID = [(beam, branch, alpha, timew, horizon, fill)
        for beam in (96, 128)
        for branch in (18, 22)
        for alpha in (5.0, 6.0, 7.0)
        for timew in (1.0, 1.2, 1.4)
        for horizon in (1.5, 2.2)
        for fill in (2, 3, 4, 6, 8)]


def run(out, seeds, trials, forward, arrival_aware, baseline=(192, 862), start=0):
    assert not out.exists()
    out.mkdir(parents=True)
    package = Path('artifacts/193_cx853')
    codes = json.loads((package / 'class_codes.json').read_text())
    recipe = json.loads((package / 'phase_search_recipe.json').read_text())
    co = np.array(recipe['co']) * math.pi
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-10}
    enc = encoders(codes, *forward)
    incoming = touches(enc)
    arrival = [incoming[w] for w in KERNEL_WIRES]
    best = tuple(baseline)
    rows = []
    wall_start = time.time()
    for index in range(seeds):
        absolute = start + index
        seed = absolute
        beam, branch, alpha, timew, horizon, fill = GRID[absolute % len(GRID)]
        rng = random.Random(seed + 771)

        def finalize(q, basis):
            initial = touches(q, arrival)
            winner = None
            for sample in range(trials):
                ops, perm, times = finish(basis, initial, rng, sample)
                score = (max(times[w] + arrival[col] for w, col in enumerate(perm)),
                         len(ops) + q.size())
                if winner is None or score < winner[0]:
                    winner = (score, ops)
            score, ops = winner
            result = q.copy()
            for a, b in ops:
                result.cx(a, b)
            return score, result

        config = dict(seed=seed, beam=beam, branch=branch, alpha=alpha, timew=timew,
                      horizon=horizon, fill=fill)
        if arrival_aware:
            config['initial_times'] = [t - min(arrival) for t in arrival]
        kernel = psynth(8, targets, global_phase=float(co[0]), finalize=finalize, **config)
        mapping = mapping_of(kernel)
        q = native(enc.compose(kernel, KERNEL_WIRES).compose(enc.inverse(), mapping))
        text = qasm2.dumps(q)
        q = qasm2.loads(text)
        score = (q.depth(), q.count_ops().get('cx', 0))
        rows.append(dict(**{k: v for k, v in config.items() if k != 'initial_times'},
                         depth=score[0], cx=score[1]))
        if score < best:
            best = score
            path = out / f'oracle_d{score[0]}_cx{score[1]}.qasm'
            path.write_text(text)
            (out / f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(
                qasm2.dumps(native(kernel)))
            (out / f'recipe_d{score[0]}_cx{score[1]}.json').write_text(json.dumps(
                dict(config={k: v for k, v in config.items() if k != 'initial_times'},
                     forward=list(forward), inverse=list(forward), mapping=mapping,
                     trials=trials), indent=2))
            print('IMPROVEMENT', score, config, flush=True)
        if index % 10 == 0:
            print('index', index, 'current', score, 'best', best,
                  'elapsed', round(time.time() - wall_start), flush=True)
        (out / 'report.json').write_text(json.dumps(
            dict(best=best, completed=index + 1, forward=list(forward),
                 trials=trials, rows=rows), indent=2))
    print('done best', best, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seeds', type=int, default=120)
    p.add_argument('--trials', type=int, default=300)
    p.add_argument('--forward', type=int, nargs=2, default=[298, 506])
    p.add_argument('--arrival-aware', action='store_true')
    p.add_argument('--baseline', type=int, nargs=2, default=[192, 862])
    p.add_argument('--start', type=int, default=0)
    a = p.parse_args()
    run(a.outdir, a.seeds, a.trials, tuple(a.forward), a.arrival_aware, tuple(a.baseline), a.start)
