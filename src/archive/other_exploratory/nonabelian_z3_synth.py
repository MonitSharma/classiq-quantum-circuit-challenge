"""Hard-constraint synthesis probe for finite-group phase programs.

Each instruction chooses one binary-icosahedral group element for input bit 0
and one for input bit 1.  The solver enforces the exact terminal condition
(+identity or -identity) on all 4096 coordinate inputs.  This is a bounded
diagnostic, not a claim that a short program exists.
"""

from __future__ import annotations

import argparse
import json
import time

import z3

from nonabelian_branch_search import IDENTITY, MULTIPLY, TARGET


def _group_array() -> z3.ArrayRef:
    integer = z3.IntSort()
    rows = []
    for state in range(len(MULTIPLY)):
        row = z3.K(integer, 0)
        for element, result in enumerate(MULTIPLY[state]):
            row = z3.Store(row, element, result)
        rows.append(row)
    table = z3.K(integer, rows[0])
    for state, row in enumerate(rows):
        table = z3.Store(table, state, row)
    return table


def solve(order: tuple[int, ...], timeout_ms: int) -> dict:
    table = _group_array()
    length = len(order)
    group_order = len(MULTIPLY)
    zero = [z3.Int(f"g0_{index}") for index in range(length)]
    one = [z3.Int(f"g1_{index}") for index in range(length)]
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    for choice in zero + one:
        solver.add(0 <= choice, choice < group_order)
    for input_index, target in enumerate(TARGET):
        state: z3.ArithRef = z3.IntVal(IDENTITY)
        for position, bit in enumerate(order):
            choice = one[position] if ((input_index >> bit) & 1) else zero[position]
            state = z3.Select(z3.Select(table, state), choice)
        solver.add(state == target)
    started = time.time()
    result = solver.check()
    payload = {
        "order": list(order),
        "length": length,
        "timeout_ms": timeout_ms,
        "solver_result": str(result),
        "elapsed_seconds": time.time() - started,
        "status": "exact" if result == z3.sat else (
            "proven_unsat" if result == z3.unsat else "timeout_or_unknown"
        ),
    }
    if result == z3.sat:
        model = solver.model()
        payload["zero_elements"] = [model.evaluate(value).as_long() for value in zero]
        payload["one_elements"] = [model.evaluate(value).as_long() for value in one]
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", nargs="+", type=int, required=True)
    parser.add_argument("--timeout-ms", type=int, default=60000)
    args = parser.parse_args()
    if any(bit < 0 or bit >= 12 for bit in args.order):
        raise SystemExit("order bits must be in 0..11")
    print(json.dumps(solve(tuple(args.order), args.timeout_ms), indent=2))


if __name__ == "__main__":
    main()
