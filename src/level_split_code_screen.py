"""Bounded exact screen for degree-bounded, three-bit level encodings.

Six nonempty level classes use six of eight codewords, so at most two
classes can split. Enumerating the 15 possible pairs is complete, unlike
assuming only level zero can split. GF(2) elimination first enforces that
the other four classes each have one code; SAT then enforces disjointness.
No quantum circuit or depth claim follows from a satisfying code.
"""
import argparse
import itertools
import json
import multiprocessing as mp
import time
from pathlib import Path
from level_degree3_codes import CNF, level_table, verify_code


def linear_screen(name, split, degree=3):
    monomials = [m for m in range(64) if m.bit_count() <= degree]
    levels = level_table(name)
    evaluations = [sum(1 << i for i, m in enumerate(monomials)
                       if m & p == m) for p in range(64)]
    pivots = {}
    for level in range(6):
        if level in split:
            continue
        points = [p for p in range(64) if levels[p] == level]
        for p in points[1:]:
            row = evaluations[p] ^ evaluations[points[0]]
            while row:
                i = row.bit_length() - 1
                if i in pivots:
                    row ^= pivots[i]
                else:
                    pivots[i] = row
                    break
    reduced = []
    for row in evaluations:
        for i in sorted(pivots, reverse=True):
            if row >> i & 1:
                row ^= pivots[i]
        reduced.append(row)
    collision = next(([p, q] for p in range(64) for q in range(p)
                      if levels[p] != levels[q] and reduced[p] == reduced[q]), None)
    return levels, reduced, len(monomials) - len(pivots), collision


def solve_worker(name, split, queue, degree=3):
    monomials = [m for m in range(64) if m.bit_count() <= degree]
    levels, rows, dimension, collision = linear_screen(name, split, degree)
    assert collision is None
    cnf = CNF()
    used = sorted({i for row in rows for i in range(len(monomials)) if row >> i & 1})
    variables = [{i: cnf.var() for i in used} for _ in range(3)]
    # Any three distinct binary codewords can be affinely mapped to 0, 1, 2.
    # Output affine transforms preserve degree, equality, and disjointness.
    fixed = [level for level in range(6) if level not in split][:3]
    for code, level in zip((0, 1, 2), fixed):
        row = rows[levels.index(level)]
        for bit in range(3):
            cnf.xor([variables[bit][i] for i in used if row >> i & 1], code >> bit & 1)
    differences = {rows[p] ^ rows[q] for p in range(64) for q in range(p)
                   if levels[p] != levels[q]}
    for diff in sorted(differences):
        cnf.solver.add_clause([
            cnf.parity_var(variables[bit][i] for i in used if diff >> i & 1)
            for bit in range(3)
        ])
    status = cnf.solver.solve()
    result = {'status': 'sat' if status else 'unsat', 'dimension': dimension}
    if status:
        model = {v for v in cnf.solver.get_model() if v > 0}
        funcs = [sum((sum(variables[bit][i] in model for i in used if row >> i & 1) % 2) << p
                     for p, row in enumerate(rows)) for bit in range(3)]
        codes = verify_code(name, funcs)
        # Independently check the requested degree from the returned truth tables.
        for truth in funcs:
            anf = [(truth >> p) & 1 for p in range(64)]
            for bit in range(6):
                for p in range(64):
                    if p >> bit & 1:
                        anf[p] ^= anf[p ^ (1 << bit)]
            assert all(not value or p.bit_count() <= degree for p, value in enumerate(anf))
        result.update(truth_tables=funcs, level_codes={str(l): sorted({codes[p] for p in range(64)
                                                                                   if levels[p] == l}) for l in range(6)})
    cnf.solver.delete()
    queue.put(result)


def run(name, seconds, degree=3):
    cases = []
    for split in itertools.combinations(range(6), 2):
        _, _, dimension, collision = linear_screen(name, split, degree)
        item = dict(split=list(split), dimension=dimension)
        if collision is not None:
            item.update(status='linear_impossible', collision=collision)
        else:
            ctx = mp.get_context('spawn')
            queue = ctx.Queue()
            process = ctx.Process(target=solve_worker, args=(name, split, queue, degree))
            start = time.monotonic()
            process.start()
            process.join(seconds)
            if process.is_alive():
                process.terminate()
                process.join()
                item['status'] = 'timeout'
            elif process.exitcode:
                item.update(status='worker_error', exitcode=process.exitcode)
            else:
                item.update(queue.get(timeout=2))
            queue.close()
            item['seconds'] = time.monotonic() - start
        cases.append(item)
        print(name, split, item['status'], flush=True)
        if item['status'] == 'sat':
            break
    return {'name': name, 'degree': degree, 'bits': 3, 'cases': cases,
            'status': 'sat' if any(c['status'] == 'sat' for c in cases) else
            'unsat' if all(c['status'] in ('unsat', 'linear_impossible') for c in cases) else 'unresolved'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', choices=['u1', 'v1', 'u2', 'v2'], required=True)
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--out', required=True)
    parser.add_argument('--degree', type=int, choices=range(1, 7), default=3)
    args = parser.parse_args()
    result = run(args.name, args.seconds, args.degree)
    Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    print('overall', result['status'], flush=True)
