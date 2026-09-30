"""Enumerate fixed-support LUT decompositions suggested by an ABC 6-LUT map.

This is a reproducible driver for the targeted screening recorded in
docs/EXPERIMENTS.md.  It deliberately treats solver ``unknown`` and CEGAR
round limits separately from UNSAT.
"""

import argparse
import itertools
import re
import time
from pathlib import Path

from lut_decomposition import (solve_joint_pysat, solve_joint_pysat_direct,
                               solve_joint_z3_array,
                               solve_joint_z3_bool, solve_supports_z3)


def abc_cut_supports(path):
    nodes = {f'x{i:02d}': {i} for i in range(12)}
    supports = set()
    pattern = re.compile(r'(new_n\d+)\s*= LUT 0x[0-9a-f]+ \( (.*) \)')
    for line in Path(path).read_text().splitlines():
        match = pattern.match(line)
        if not match:
            continue
        name, args = match.groups()
        args = [arg.strip() for arg in args.split(',')]
        support = set().union(*(nodes[arg] for arg in args))
        nodes[name] = support
        if len(support) == 6:
            supports.add(tuple(sorted(support)))
    return sorted(supports)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bench', default='experiments/logo.bench')
    parser.add_argument('--k', type=int, choices=(4, 5), required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--time-limit', type=float, default=1.5)
    parser.add_argument('--joint', action='store_true',
                        help='choose arbitrary supports and tables jointly')
    parser.add_argument('--direct', action='store_true',
                        help='encode all 4096 inputs in one exact SAT model')
    parser.add_argument('--encoding', choices=('array', 'bool', 'pysat'),
                        default='array', help='joint solver encoding')
    parser.add_argument('--initial-pairs', type=int, default=120)
    parser.add_argument('--rounds', type=int, default=30)
    parser.add_argument('--collision-batch', type=int, default=1000)
    parser.add_argument('--conflict-budget', type=int)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    if args.direct:
        model, info = solve_joint_pysat_direct(
            k=args.k, conflict_budget=args.conflict_budget, verbose=True)
        print('RESULT', model, info, flush=True)
        return 0

    if args.joint:
        solver = {
            'array': solve_joint_z3_array,
            'bool': solve_joint_z3_bool,
            'pysat': solve_joint_pysat,
        }[args.encoding]
        kwargs = {
            'k': args.k, 'initial_pairs': args.initial_pairs,
            'rounds': args.rounds, 'collision_batch': args.collision_batch,
            'seed': args.seed, 'verbose': False,
        }
        if args.encoding == 'pysat':
            kwargs['conflict_budget'] = args.conflict_budget
        if args.encoding != 'pysat':
            kwargs['time_limit'] = args.time_limit
        model, info = solver(**kwargs)
        print('RESULT', model, info, flush=True)
        return 0

    supports = abc_cut_supports(args.bench)
    combinations = list(itertools.combinations(supports, args.k))
    if args.limit is not None:
        combinations = combinations[:args.limit]
    counts = {}
    start = time.time()
    for index, candidate in enumerate(combinations):
        model, info = solve_supports_z3(
            candidate, initial_pairs=100, rounds=12,
            collision_batch=3000, time_limit=args.time_limit,
            seed=index, verbose=False,
        )
        counts[info['status']] = counts.get(info['status'], 0) + 1
        if model:
            print('FOUND', index, model, info, flush=True)
            return 0
        if index % 50 == 0:
            print(index, counts, round(time.time() - start, 1), flush=True)
    print('DONE', len(combinations), counts,
          'elapsed', round(time.time() - start, 1), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
