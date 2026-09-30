"""Bounded affine-frame SAT refinement for five-batch beam topologies.

Frames are explicit invertible 9x9 GF(2) maps with translations.  The model is
solved on a sample, then the extracted matrices are replayed on all 64 inputs;
storage is measured independently from the concrete replay.
"""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path
import z3

from post137_joint_encoder_cosynth import (VARS, FULL, apply, beam_side,
                                           nonlinear_storage, wanted_tables)

def packed(table, points):
    return sum(((table >> p) & 1) << i for i, p in enumerate(points))

def parity(values):
    if not values: return z3.BoolVal(False)
    out = values[0]
    for value in values[1:]: out = z3.Xor(out, value)
    return out

def affine_frame(s, rows, tag, width):
    mat = [[z3.Bool(f'{tag}_m_{i}_{j}') for j in range(width)] for i in range(width)]
    inv = [[z3.Bool(f'{tag}_i_{i}_{j}') for j in range(width)] for i in range(width)]
    trans = [z3.Bool(f'{tag}_c_{i}') for i in range(width)]
    for i in range(width):
        for j in range(width):
            s.add(parity([z3.And(mat[i][k], inv[k][j]) for k in range(width)]) == (i == j))
    out = []
    for i in range(width):
        value = z3.BitVecVal(0, rows[0].size())
        for j in range(width): value = z3.If(mat[i][j], value ^ rows[j], value)
        out.append(z3.If(trans[i], value ^ z3.BitVecVal((1 << rows[0].size()) - 1, rows[0].size()), value))
    return out, mat, inv, trans

def storage_constraint(s, rows, base, tag, limit=6):
    """Require at most ``limit`` rows to be outside the affine input span."""
    flags = []
    for i, row in enumerate(rows):
        affine = z3.Bool(f'{tag}_affine_{i}'); flags.append(affine)
        coeff = [z3.Bool(f'{tag}_coef_{i}_{j}') for j in range(7)]
        value = z3.BitVecVal(0, row.size())
        for j, source in enumerate(base + [z3.BitVecVal((1 << row.size()) - 1, row.size())]):
            value = z3.If(coeff[j], value ^ source, value)
        s.add(z3.Implies(affine, row == value))
    s.add(z3.Sum([z3.If(flag, 0, 1) for flag in flags]) <= limit)

def solve_seed(side, batches, points, timeout_ms=3000):
    wanted = wanted_tables()[side]; n = len(points); width = 9
    s = z3.Solver(); s.set(timeout=timeout_ms)
    mask = (1 << n) - 1
    rows = [z3.BitVecVal(packed(v, points), n) for v in VARS] + [z3.BitVecVal(0, n)] * 3
    base = rows[:6]
    frames = []
    for stage, batch in enumerate(batches):
        rows, mat, inv, trans = affine_frame(s, rows, f'{side}_f{stage}', width)
        frames.append((mat, inv, trans))
        storage_constraint(s, rows, base, f'{side}_pre{stage}')
        old = rows[:]
        for a, b, target in batch: rows[target] = old[target] ^ (old[a] & old[b])
        storage_constraint(s, rows, base, f'{side}_post{stage}')
    rows, mat, inv, trans = affine_frame(s, rows, f'{side}_f{len(batches)}', width)
    frames.append((mat, inv, trans))
    storage_constraint(s, rows, base, f'{side}_final')
    for i in range(3): s.add(rows[6+i] == z3.BitVecVal(packed(wanted[i], points), n))
    started = time.monotonic(); status = s.check(); elapsed = time.monotonic() - started
    result = {'side': side, 'status': str(status), 'seconds': elapsed,
              'timeout_ms': timeout_ms, 'sample_size': n, 'batches': batches}
    if status != z3.sat:
        if status == z3.unknown: result['reason'] = s.reason_unknown()
        return result, None
    model = s.model(); extracted = []
    for mat, inv, trans in frames:
        extracted.append({'matrix': [[int(z3.is_true(model.eval(v, model_completion=True))) for v in row] for row in mat],
                          'inverse': [[int(z3.is_true(model.eval(v, model_completion=True))) for v in row] for row in inv],
                          'translation': [int(z3.is_true(model.eval(v, model_completion=True))) for v in trans]})
    result['frames'] = extracted
    return result, extracted

def replay(side, batches, frames):
    wanted = wanted_tables()[side]; rows = VARS[:] + [0, 0, 0]
    profile = []
    def frame_apply(fr, values):
        out = []
        for i, row in enumerate(fr['matrix']):
            value = 0
            for j, enabled in enumerate(row):
                if enabled: value ^= values[j]
            if fr['translation'][i]: value ^= FULL
            out.append(value)
        return out
    for stage, batch in enumerate(batches):
        rows = frame_apply(frames[stage], rows); old = rows[:]
        for a, b, target in batch: rows[target] = old[target] ^ (old[a] & old[b])
        profile.append(nonlinear_storage(tuple(rows)))
    rows = frame_apply(frames[-1], rows)
    bad = [i for i, target in enumerate(wanted) if rows[6+i] != target]
    return {'exact': not bad, 'bad_outputs': bad, 'storage_profile': profile,
            'peak_storage': max(profile, default=0), 'within_six_slots': max(profile, default=0) <= 6}

def run(seconds=5, seed=137, timeout_ms=1500):
    start = time.monotonic(); rng = random.Random(seed); result = {'status': 'complete', 'sides': {}}
    for side in ('x', 'y'):
        points = sorted(rng.sample(range(64), 8)); beam = beam_side(wanted_tables()[side], points, 5, rng, width=1)
        if not beam: result['sides'][side] = {'status': 'NO_BEAM'}; continue
        _, batches = beam[0]; rec, frames = solve_seed(side, batches, points, timeout_ms)
        rec['beam_points'] = points
        if frames is not None: rec['replay'] = replay(side, batches, frames)
        result['sides'][side] = rec
        if time.monotonic() - start > seconds: break
    result['elapsed_seconds'] = time.monotonic() - start
    return result

def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True); p.add_argument('--seconds', type=float, default=5); p.add_argument('--seed', type=int, default=137); p.add_argument('--timeout-ms', type=int, default=1500); a = p.parse_args()
    r = run(a.seconds, a.seed, a.timeout_ms); a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(r, indent=2)+'\n'); print(json.dumps(r, indent=2))
if __name__ == '__main__': main()
