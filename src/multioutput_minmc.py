"""Bounded shared-XAG search for multiple six-variable feature outputs.

Every Boolean signal is represented as a 64-bit truth signature.  The Z3
search asks for shared affine-AND nodes whose final affine combinations equal
all requested outputs.  Models are independently evaluated with integer bit
operations before being reported.
"""
from __future__ import annotations

import argparse
import functools
import json
import time
from pathlib import Path

import z3

from radius import R, radius
from search import truth


FULL = (1 << 64) - 1
INPUTS = [sum(1 << row for row in range(64) if row & (1 << bit)) for bit in range(6)]
FEATURES = {
    "R0": R[0], "R1": R[1], "R2": R[2],
    "A": truth(range(29, 54)), "B": truth(range(39, 44)),
    "V": truth(y for y in range(64) if radius(y) > 0),
}


def affine(coefficients, signals):
    result = z3.BitVecVal(0, 64)
    for coefficient, signal in zip(coefficients, signals):
        result = result ^ z3.If(coefficient, signal, z3.BitVecVal(0, 64))
    return result


def mask_from_model(model, coefficients):
    return sum(1 << i for i, c in enumerate(coefficients)
               if z3.is_true(model.eval(c, model_completion=True)))


def eval_xag(xag):
    signals = [FULL, *INPUTS]
    for node in xag["and_nodes"]:
        left = 0
        right = 0
        for i in node["left"]:
            left ^= signals[i]
        for i in node["right"]:
            right ^= signals[i]
        signals.append(left & right)
    return [functools.reduce(int.__xor__, (signals[i] for i in output), 0)
            for output in xag["outputs"]]


def synthesize(targets, max_and=8, timeout_ms=5000):
    started = time.time()
    for count in range(max_and + 1):
        solver = z3.Solver()
        solver.set(timeout=timeout_ms)
        signals = [z3.BitVecVal(FULL, 64), *[z3.BitVecVal(x, 64) for x in INPUTS]]
        node_specs = []
        for node in range(count):
            left_coeff = [z3.Bool(f"l_{node}_{i}") for i in range(len(signals))]
            right_coeff = [z3.Bool(f"r_{node}_{i}") for i in range(len(signals))]
            solver.add(z3.Or(left_coeff), z3.Or(right_coeff))
            signals.append(affine(left_coeff, signals) & affine(right_coeff, signals))
            node_specs.append((left_coeff, right_coeff))
        outputs = [[z3.Bool(f"o_{j}_{i}") for i in range(len(signals))]
                   for j in range(len(targets))]
        for target, coefficients in zip(targets, outputs):
            solver.add(affine(coefficients, signals) == z3.BitVecVal(target, 64))
        result = solver.check()
        if result != z3.sat:
            continue
        model = solver.model()
        nodes = []
        for left, right in node_specs:
            lm, rm = mask_from_model(model, left), mask_from_model(model, right)
            nodes.append({"left": [i for i in range(len(signals) - 1) if lm >> i & 1],
                          "right": [i for i in range(len(signals) - 1) if rm >> i & 1]})
        output_lists = []
        for coefficients in outputs:
            mask = mask_from_model(model, coefficients)
            output_lists.append([i for i in range(len(signals)) if mask >> i & 1])
        candidate = {"and_count": count, "and_nodes": nodes, "outputs": output_lists}
        if eval_xag(candidate) != targets:
            raise AssertionError("multi-output XAG model failed independent verification")
        candidate["elapsed_seconds"] = time.time() - started
        return candidate
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-and", type=int, default=8)
    parser.add_argument("--timeout-ms", type=int, default=5000)
    args = parser.parse_args()
    groups = [("R0", "R1"), ("R1", "R2"), ("A", "B"), ("A", "B", "V")]
    rows = []
    for names in groups:
        print("searching", names, flush=True)
        result = synthesize([FEATURES[name] for name in names], args.max_and, args.timeout_ms)
        rows.append({"features": list(names), "result": result,
                     "status": "exact" if result else "unknown_or_above_bound"})
    report = {"backend": "bounded_shared_multioutput_xag", "max_and": args.max_and,
              "timeout_ms_per_bound": args.timeout_ms, "rows": rows}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
