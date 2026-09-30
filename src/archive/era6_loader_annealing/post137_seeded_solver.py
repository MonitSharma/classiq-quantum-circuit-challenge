"""Seed the bounded reversible solver from storage-feasible beam paths.

The existing Z3 backend exposes a different gate parameterization, so the
safe integration point is its CEGIS constraint set: beam counterexamples are
carried into the solver sample set, and every returned model is replayed on
all 64 inputs before promotion.
"""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path

from post137_joint_encoder_cosynth import beam_side, reduce_by, wanted_tables, storage_profile
from post190_joint_reversible import solve, evaluate

def run_side(side, seed, timeout, sample_size=8, beam_width=24):
    wanted = wanted_tables(); rng = random.Random(seed)
    initial = sorted(rng.sample(range(64), sample_size))
    beam = beam_side(wanted[side], initial, 5, rng, width=beam_width)
    if not beam:
        return {'side': side, 'status': 'NO_STORAGE_FEASIBLE_BEAM'}
    rows, batches = beam[0]
    # CEGIS seed: include beam failures, then let the solver refine its own model.
    basis = list(rows) + [(1 << 64) - 1]
    bad = 0
    for target in wanted[side]: bad |= reduce_by(target, basis)
    points = sorted(set(initial) | {p for p in range(64) if bad >> p & 1})
    points = points[:64]
    record, ops = solve(side, points, stages=5, seconds=timeout / 1000, split=True)
    out = {'side': side, 'beam_sample_size': len(initial), 'solver_sample_size': len(points),
           'beam_storage': storage_profile(batches), 'beam_batches': batches, 'solver': record}
    if ops is None:
        out['replay'] = 'NOT_RUN'
        return out
    bad, words, codes = evaluate(ops, side, split=True)
    out['full_bad_inputs'] = len(bad)
    out['replay'] = 'EXACT' if not bad else 'FAILED'
    if not bad: out['ops'] = ops
    return out

def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--timeout-ms', type=int, default=3000); p.add_argument('--seed', type=int, default=137)
    a = p.parse_args(); start = time.monotonic()
    result = {'status': 'complete', 'timeout_ms': a.timeout_ms,
              'x': run_side('x', a.seed, a.timeout_ms), 'y': run_side('y', a.seed+1, a.timeout_ms)}
    result['elapsed_seconds'] = time.monotonic() - start
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, indent=2, default=list)+'\n')
    print(json.dumps(result, indent=2, default=list))

if __name__ == '__main__': main()
