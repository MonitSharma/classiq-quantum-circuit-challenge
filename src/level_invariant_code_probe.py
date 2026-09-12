"""Search split level codes whose bits each omit an affine input direction.

Unlike fixed codeword searches, points in one level may use several codes.
No circuit artifacts are overwritten. This is a classical feasibility probe.
"""
import argparse
import itertools
import json
import time
from pathlib import Path
from level_oracle import LEVEL
from level_degree3_codes import CNF, verify_code


def partition(levels, split, direction):
    parent = list(range(64))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    def merge(a, b):
        parent[find(a)] = find(b)
    for p in range(64):
        merge(p, p ^ direction)
    for level in range(6):
        if level not in split:
            points = [p for p in range(64) if levels[p] == level]
            for p in points[1:]:
                merge(points[0], p)
    roots = [find(p) for p in range(64)]
    labels = {r: i for i, r in enumerate(sorted(set(roots)))}
    return [labels[r] for r in roots]


def solve(name, parts, pairs):
    cnf = CNF()
    bits = [[cnf.var() for _ in range(max(part)+1)] for part in parts]
    # Complementing each bit is free and preserves every input invariance.
    for vs, part in zip(bits, parts):
        cnf.solver.add_clause([-vs[part[0]]])
    cache = {}
    for p, q in pairs:
        differences = []
        for bit in range(3):
            a, b = sorted((parts[bit][p], parts[bit][q]))
            if a == b:
                continue
            key = bit, a, b
            if key not in cache:
                cache[key] = cnf.parity_var([bits[bit][a], bits[bit][b]])
            differences.append(cache[key])
        cnf.solver.add_clause(differences)
    cnf.solver.conf_budget(100000)
    status = cnf.solver.solve_limited()
    result = {'status': 'unknown' if status is None else 'sat' if status else 'unsat'}
    if status:
        model = {v for v in cnf.solver.get_model() if v > 0}
        funcs = [sum((vs[part[p]] in model) << p for p in range(64))
                 for vs, part in zip(bits, parts)]
        codes = verify_code(name, funcs)
        result.update(tables=funcs, codes=codes)
    cnf.solver.delete()
    return result


def run(name, seconds):
    start = time.monotonic()
    levels = LEVEL[name]
    pairs = [(p, q) for p in range(64) for q in range(p) if levels[p] != levels[q]]
    cases = []
    # At most two of six levels can split across eight codewords.
    for split in itertools.combinations(range(6), 2):
        parts = [partition(levels, split, d) for d in range(1, 64)]
        collisions = [sum((part[p] == part[q]) << i for i, (p, q) in enumerate(pairs))
                      for part in parts]
        stats = dict(split=split, screened=0, possible=0, unsat=0, unknown=0)
        for dirs in itertools.combinations_with_replacement(range(63), 3):
            stats['screened'] += 1
            if collisions[dirs[0]] & collisions[dirs[1]] & collisions[dirs[2]]:
                continue
            stats['possible'] += 1
            result = solve(name, [parts[d] for d in dirs], pairs)
            if result['status'] == 'sat':
                ds = [d+1 for d in dirs]
                for table, direction in zip(result['tables'], ds):
                    assert all((table >> p & 1) == (table >> (p ^ direction) & 1) for p in range(64))
                return dict(name=name, status='sat', split=split, directions=ds,
                            witness=result, cases=cases+[stats], seconds=time.monotonic()-start)
            stats[result['status']] += 1
            if time.monotonic()-start > seconds:
                return dict(name=name, status='timeout', cases=cases+[stats])
        cases.append(stats)
        print(name, stats, flush=True)
    return dict(name=name, status='unknown' if any(c['unknown'] for c in cases) else 'unsat',
                cases=cases, seconds=time.monotonic()-start)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', choices=list(LEVEL), required=True)
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    result = run(args.name, args.seconds)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
