"""Search for a nine-register AND network that exposes a level-separating code.

Each level encoder must turn six coordinate bits into three bits that separate
the six level values.  Nine wires are available per side: the six data wires,
which may be scrambled because the encoder is inverted after the kernel, plus
three clean ancillas.  Because the encoder always sits inside an exact
compute/uncompute sandwich, relative-phase Toffolis are sound, so every AND is
one RCCX.

Usage:  python src/level_encoder_search.py u1 <seed> <seconds> <outdir>

Writes ``net_<name>_<seed>.json`` holding the AND list and the separating code,
which ``level_oracle.load_nets`` consumes.
"""
import json
import random
import sys
import time
from pathlib import Path

FULL = (1 << 64) - 1
VARS = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]


def _rng(a, b):
    return set(range(a, b + 1))


NESTED = {
    'u1': [_rng(11, 27), _rng(12, 26), _rng(13, 25), _rng(15, 23), _rng(17, 21)],
    'v1': [_rng(32, 48), _rng(33, 47), _rng(34, 46), _rng(36, 44), _rng(38, 42)],
    'u2': [_rng(29, 53), _rng(35, 47), _rng(36, 46), _rng(37, 45), _rng(39, 43)],
    'v2': [_rng(2, 61), _rng(2, 26) | _rng(50, 60), _rng(2, 26) | _rng(51, 59),
           _rng(2, 26) | _rng(53, 57), _rng(2, 26)],
}


def reduce_basis(vectors):
    piv = {}
    for v in vectors:
        for b in range(63, -1, -1):
            if v >> b & 1:
                if b in piv:
                    v ^= piv[b]
                else:
                    piv[b] = v
                    break
    return piv


def residual(v, piv):
    for b in range(63, -1, -1):
        if v >> b & 1 and b in piv:
            v ^= piv[b]
    return v


def separating_triples():
    out = []
    for a in range(1, 64):
        for b in range(a + 1, 64):
            for c in range(b + 1, 64):
                sig = {((a >> k) & 1, (b >> k) & 1, (c >> k) & 1) for k in range(6)}
                if len(sig) == 6:
                    out.append((a, b, c))
    return out


def search(name, seed, limit, beam=30, tries=6000, max_ands=20):
    levels = [sum(1 for s in NESTED[name] if t in s) for t in range(64)]
    indicators = [sum(1 << t for t in range(64) if levels[t] == k) for k in range(6)]
    subsets = [sum(indicators[k] for k in range(6) if S >> k & 1) for S in range(64)]
    triples = separating_triples()
    rng = random.Random(seed)

    def score(regs):
        piv = reduce_basis(list(regs) + [FULL])
        weight = [bin(residual(subsets[S], piv)).count('1') for S in range(64)]
        best = 10 ** 9
        for a, b, c in triples:
            s = weight[a] + weight[b] + weight[c]
            if s < best:
                best = s
                if s == 0:
                    return 0, (a, b, c)
        return best, None

    def operand(regs):
        a = 0
        for _ in range(rng.randint(1, 3)):
            a ^= regs[rng.randrange(9)]
        return a ^ FULL if rng.random() < 0.5 else a

    start = tuple(VARS + [0, 0, 0])
    states = [(score(start)[0], start, ())]
    began = time.time()
    for step in range(max_ands):
        cand = {}
        for _, regs, hist in states:
            seen = set()
            for _ in range(tries):
                a, b = operand(regs), operand(regs)
                p = a & b
                if p in (0, FULL):
                    continue
                k = rng.randrange(9)
                nxt = list(regs)
                nxt[k] ^= p
                nxt = tuple(nxt)
                if nxt in seen:
                    continue
                seen.add(nxt)
                value, _ = score(nxt)
                key = tuple(sorted(nxt))
                if key not in cand or cand[key][0] > value:
                    cand[key] = (value, nxt, hist + ((a, b, k),))
        if not cand:
            return None
        states = sorted(cand.values(), key=lambda z: z[0])[:beam]
        print(f'{name} seed{seed} ands={step + 1} residual={states[0][0]} '
              f't={time.time() - began:.0f}s', flush=True)
        if states[0][0] == 0:
            _, triple = score(states[0][1])
            return dict(name=name, ands=step + 1, triple=list(triple),
                        hist=[[a, b, k] for a, b, k in states[0][2]])
        if time.time() - began > limit:
            print('time limit reached', flush=True)
            return None
    return None


if __name__ == '__main__':
    name = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    limit = float(sys.argv[3]) if len(sys.argv) > 3 else 1200
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 else Path('artifacts/level_nets')
    result = search(name, seed, limit)
    if result is None:
        raise SystemExit('no separating network found within the limit')
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f'net_{name}_{seed}.json'
    path.write_text(json.dumps(result, indent=2))
    print('wrote', path)
