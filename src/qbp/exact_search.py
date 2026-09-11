"""Bounded exact Z3 search for finite-group width-2 QBPs."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import z3

from qbp.finite_group import (
    CENTRALIZER_ORBIT_REPS,
    CONJUGACY_REPRESENTATIVES,
    IDENTITY,
    MULTIPLY,
    TARGET,
)


def _group_array() -> z3.ArrayRef:
    integer = z3.IntSort()
    rows = []
    for state, values in enumerate(MULTIPLY):
        row = z3.K(integer, 0)
        for element, result in enumerate(values):
            row = z3.Store(row, element, result)
        rows.append(row)
    table = z3.K(integer, rows[0])
    for state, row in enumerate(rows):
        table = z3.Store(table, state, row)
    return table


def solve(order: tuple[int, ...], timeout_ms: int, symmetry_breaking: bool = True) -> dict:
    table = _group_array()
    length = len(order)
    zero = [z3.Int(f"zero_{i}") for i in range(length)]
    one = [z3.Int(f"one_{i}") for i in range(length)]
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    for choice in zero + one:
        solver.add(0 <= choice, choice < len(MULTIPLY))
    if symmetry_breaking and length:
        # Simultaneous conjugation maps every transition g to h^-1*g*h and
        # preserves the central terminal targets (+I and -I).  Choose one
        # representative for the first zero transition, then one representative
        # under its residual centralizer.  This is exact symmetry breaking.
        solver.add(z3.Or(*[zero[0] == rep for rep in CONJUGACY_REPRESENTATIVES]))
        for rep, allowed in CENTRALIZER_ORBIT_REPS.items():
            solver.add(z3.Implies(zero[0] == rep, z3.Or(*[one[0] == value for value in allowed])))
    # Materialize each input/time state as a named finite-domain variable.  It
    # is logically equivalent to nested Select expressions, but lets Z3 learn
    # and propagate intermediate domains across the 4096 trajectories.
    states = [[z3.Int(f"state_{input_index}_{position}") for position in range(length + 1)]
              for input_index in range(4096)]
    for input_index, target in enumerate(TARGET):
        solver.add(states[input_index][0] == IDENTITY)
        for position, bit in enumerate(order):
            selected = one[position] if ((input_index >> bit) & 1) else zero[position]
            solver.add(
                states[input_index][position + 1]
                == z3.Select(z3.Select(table, states[input_index][position]), selected)
            )
            solver.add(0 <= states[input_index][position + 1], states[input_index][position + 1] < len(MULTIPLY))
        solver.add(states[input_index][length] == target)
    started = time.time()
    status = solver.check()
    result = {
        "order": list(order),
        "length": length,
        "timeout_ms": timeout_ms,
        "solver_result": str(status),
        "elapsed_seconds": time.time() - started,
        "status": "exact" if status == z3.sat else (
            "proven_unsat" if status == z3.unsat else "timeout_or_unknown"
        ),
        "symmetry_breaking": symmetry_breaking,
    }
    if status == z3.sat:
        model = solver.model()
        result["zero_elements"] = [model.evaluate(value).as_long() for value in zero]
        result["one_elements"] = [model.evaluate(value).as_long() for value in one]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=12)
    parser.add_argument("--timeout-ms", type=int, default=5000)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    order = tuple((0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)[i % 12] for i in range(args.length))
    payload = solve(order, args.timeout_ms)
    payload.update({
        "kind": "exact finite-group QBP checkpoint",
        "group": "binary_icosahedral",
        "group_order": len(MULTIPLY),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    })
    print(json.dumps(payload, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
