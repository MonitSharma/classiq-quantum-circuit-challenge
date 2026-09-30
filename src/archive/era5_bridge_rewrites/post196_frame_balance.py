"""Search class codes against a loader frame *lower bound*, not the term count.

`structured_ucry` spends, in frame `f`, one CX and one Rz per Walsh mask that
its six hosts must visit.  A host is blocked by its own operations and the three
low wires are the only CX controls, so the frame needs at least

    max( 2 * max_host_load , ceil(total_masks_in_frame / 3) )

layers, and the loader needs the sum over four frames plus about thirteen layers
of frame skeleton.  That is a *balance* objective: 174 terms spread evenly over
the twenty-four (host, frame) slots cost 58 layers, while the same 174 terms with
one slot holding eight masks cost 64.  Earlier searches minimised the total
Walsh support instead, which is why they kept trading a cheaper loader for a much
dearer kernel.

This is a lower bound, not the schedule cost.  `post196_frame_model_audit.py`
exhibits six hosts each needing low masks {0, 1}: every closed tour toggles low
wire 0 twice, so that one wire needs twelve CX and an explicit schedule takes 13
layers, while the host/average-source terms alone return 4.  The third term
below closes that particular gap -- a tour that visits any mask with bit `k` set
must toggle bit `k` at least twice, since it starts and ends at 0 -- but the
joint scheduling problem is not solved here and other gaps may remain.

For the recorded 218 codes the bound is 77 at its best high/low split, and the
compiled loader achieves 77.  A bound that is attained is an optimum *for those
codes within this frame design*; it says nothing about other codes, for which
the bound can be loose (68 predicted against 70 measured on one annealed
alternative).
"""
import argparse
import itertools
import json
import math
import random
from pathlib import Path

import numpy as np

from two_stage_oracle import ROWCLS, COLCLS, logo

H6 = np.array([[1.0]])
for _ in range(6):
    H6 = np.block([[H6, H6], [H6, -H6]])
H6 = H6 / 64.0

ORDER8 = sorted(range(256), key=lambda m: (m.bit_count(), m))
EVAL8 = [sum(1 << i for i, m in enumerate(ORDER8) if m & ~w == 0) for w in range(256)]
H8 = np.array([[1.0]])
for _ in range(8):
    H8 = np.block([[H8, H8], [H8, -H8]])
H8 = H8 / 256.0

SKELETON = 13


def _tour_table():
    """Minimum closed Hamming tour length from 0 through each subset of the 3-cube."""
    best = [0] * 256
    for subset in range(1, 256):
        nodes = [m for m in range(8) if subset >> m & 1]
        index = {m: i for i, m in enumerate(nodes)}
        size = len(nodes)
        inf = 99
        dp = [[inf] * size for _ in range(1 << size)]
        for m in nodes:
            dp[1 << index[m]][index[m]] = m.bit_count()
        for mask in range(1 << size):
            for last in range(size):
                cost = dp[mask][last]
                if cost >= inf:
                    continue
                for nxt in range(size):
                    if mask >> nxt & 1:
                        continue
                    step = (nodes[last] ^ nodes[nxt]).bit_count()
                    target = mask | (1 << nxt)
                    if cost + step < dp[target][nxt]:
                        dp[target][nxt] = cost + step
        full = (1 << size) - 1
        best[subset] = min(dp[full][i] + nodes[i].bit_count() for i in range(size))
    return best


TOUR = _tour_table()
# A closed tour from 0 that visits any mask with bit k set must toggle bit k an
# even, nonzero number of times, so it uses low wire k at least twice.
TOUCH = [[2 if any((m >> k) & 1 for m in range(8) if subset >> m & 1) else 0
          for k in range(3)] for subset in range(256)]
SPLITS = [(combo, perm)
          for combo in itertools.combinations(range(6), 3)
          for perm in itertools.permutations(combo)]


def shifts_of(frame):
    gray = frame ^ (frame >> 1)
    return [sum(((gray >> k) & 1) << ((i + k + 1) % 3) for k in range(2)) for i in range(3)]


FRAME_SHIFTS = [shifts_of(f) for f in range(4)]
SPLIT_TABLES = {}


def split_tables(high):
    """For one high-wire choice: each mask's high pattern and low-mask bit."""
    key = tuple(high)
    if key not in SPLIT_TABLES:
        low = [i for i in range(6) if i not in high]
        pattern = np.array([sum(((m >> high[k]) & 1) << k for k in range(3))
                            for m in range(64)])
        lowbit = np.array([1 << sum(((m >> low[k]) & 1) << k for k in range(3))
                           for m in range(64)], dtype=np.int64)
        SPLIT_TABLES[key] = (pattern, lowbit)
    return SPLIT_TABLES[key]


TOUR_ARRAY = None
BUSY_ARRAY = None


def loader_floor(tables):
    """Lowest frame cost over every high-wire choice and output pairing.

    Per (host, frame) the host must visit a subset of the three low-bit masks,
    which costs `TOUR[subset]` CX gates and `popcount(subset)` rotations; the
    host is busy for the sum of those, and the three low wires can supply only
    three CX gates per layer.
    """
    global TOUR_ARRAY, BUSY_ARRAY
    if TOUR_ARRAY is None:
        TOUR_ARRAY = np.array(TOUR)
        BUSY_ARRAY = np.array([bin(s).count('1') + TOUR[s] for s in range(256)])
    spectrum = np.abs(tables @ H6.T) > 1e-9
    best = None
    for _, high in SPLITS:
        pattern, lowbit = split_tables(high)
        subsets = np.zeros((3, 8), dtype=np.int64)
        for t in range(3):
            sel = spectrum[t]
            np.bitwise_or.at(subsets[t], pattern[sel], lowbit[sel])
        total = 0
        for frame in range(4):
            shifts = FRAME_SHIFTS[frame]
            picks = [int(subsets[i][hp]) for i in range(3)
                     for hp in (shifts[i], shifts[i] ^ (1 << i))]
            contention = max(sum(TOUCH[s][k] for s in picks) for k in range(3))
            total += max(int(BUSY_ARRAY[picks].max()),
                         -(-int(TOUR_ARRAY[picks].sum()) // 3),
                         contention)
        if best is None or total < best[0]:
            best = (int(total), high)
    return best[0] + SKELETON, best[1]


def cells_of(cls, rho):
    order, index = [], {}
    for v in range(64):
        key = ((v & rho).bit_count() & 1, cls[v])
        if key not in index:
            index[key] = len(order)
            order.append(key)
    members = [[] for _ in order]
    for v in range(64):
        members[index[((v & rho).bit_count() & 1, cls[v])]].append(v)
    return order, members


def tables_of(members, labels):
    tables = np.zeros((3, 64))
    for cell, label in enumerate(labels):
        for b in range(3):
            if label >> b & 1:
                tables[b, members[cell]] = math.pi
    return tables


def codes_of(order, members, labels, rho):
    code = [0] * 64
    for cell, label in enumerate(labels):
        for v in members[cell]:
            code[v] = order[cell][0] | (label << 1)
    return code


def kernel_terms(ycode, xcode):
    want = {}
    for y in range(64):
        for x in range(64):
            key = ycode[y] | (xcode[x] << 4)
            value = 1 if logo(x, y) else 0
            if want.setdefault(key, value) != value:
                return None
    piv = {}
    for w, value in want.items():
        row, rhs = EVAL8[w], value
        while row:
            i = (row & -row).bit_length() - 1
            if i in piv:
                a, b = piv[i]
                row ^= a
                rhs ^= b
            else:
                piv[i] = (row, rhs)
                break
        else:
            if rhs:
                return None
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    counts = np.array([(EVAL8[w] & sol).bit_count() for w in range(256)], float)
    return int((np.abs(counts @ H8.T) > 1e-9).sum())


def search(outdir, steps, seed, xrho, start=None):
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    sides = []
    for cls, rho in ((ROWCLS, 32), (COLCLS, xrho)):
        order, members = cells_of(cls, rho)
        fibers = {}
        for cell, key in enumerate(order):
            fibers.setdefault(key[0], []).append(cell)
        assert all(len(v) <= 8 for v in fibers.values())
        labels = [0] * len(order)
        for group in fibers.values():
            for i, cell in enumerate(group):
                labels[cell] = i
        sides.append([order, members, fibers, labels, rho])
    if start:
        for side, key in enumerate(('ylab', 'xlab')):
            given = {tuple(map(int, k.split(','))): v for k, v in start[key].items()}
            order = sides[side][0]
            if set(given) == set(order):
                sides[side][3] = [given[k] for k in order]

    def evaluate():
        floors, codes = [], []
        for order, members, _, labels, rho in sides:
            floor, _ = loader_floor(tables_of(members, labels))
            floors.append(floor)
            codes.append(codes_of(order, members, labels, rho))
        tk = kernel_terms(codes[0], codes[1])
        if tk is None:
            return None
        return max(floors), tk, floors, codes

    def score(state):
        # 0.48 calibrated on the 218 codes: 2*77 + 0.48*90 = 197 against 196 measured
        return 2 * state[0] + 0.48 * state[1]

    state = evaluate()
    cur = score(state)
    best, best_state = cur, state
    history = []
    for step in range(steps):
        which = rng.randrange(2)
        order, members, fibers, labels, rho = sides[which]
        group = rng.choice(list(fibers.values()))
        cell = rng.choice(group)
        value = rng.randrange(8)
        other = next((c for c in group if labels[c] == value), None)
        previous = labels[cell]
        labels[cell] = value
        if other is not None:
            labels[other] = previous
        got = evaluate()
        value_score = score(got) if got else 1e9
        temp = 0.8 + 9.0 * (1 - (step % 1500) / 1500)
        if value_score <= cur or rng.random() < math.exp(min(0.0, (cur - value_score) / temp)):
            cur, state = value_score, got
            if value_score < best:
                best, best_state = value_score, got
                history.append(dict(step=step, loader_floor=got[0], kernel_terms=got[1],
                                    predicted=round(value_score, 1)))
                print(history[-1], flush=True)
        else:
            labels[cell] = previous
            if other is not None:
                labels[other] = value
    report = dict(seed=seed, steps=steps, x_rho=xrho, loader_floor=best_state[0],
                  per_side_floor=best_state[2], kernel_terms=best_state[1],
                  predicted=round(best, 1), ycode=best_state[3][0], xcode=best_state[3][1],
                  improvements=history)
    (outdir / f'balance_seed{seed}_rho{xrho}.json').write_text(json.dumps(report, indent=1) + '\n')
    print('best', report['predicted'], 'floor', report['per_side_floor'],
          'kernel terms', report['kernel_terms'], flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--steps', type=int, default=12000)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--xrho', type=int, default=48)
    p.add_argument('--start', type=Path, default=None)
    a = p.parse_args()
    search(a.outdir, a.steps, a.seed, a.xrho,
           json.loads(a.start.read_text()) if a.start else None)
