"""Bounded exact XAG search for the eight-variable branch-3 cofactor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import z3

from conditionally_clean_cofactor import cofactor_table, residual_coordinates


WIDTH = 256
FULL = (1 << WIDTH) - 1
INPUTS = [sum(1 << row for row in range(WIDTH) if row & (1 << bit)) for bit in range(8)]


def xor_selected(coefficients, signals):
    result = z3.BitVecVal(0, WIDTH)
    for coefficient, signal in zip(coefficients, signals):
        result = result ^ z3.If(coefficient, signal, z3.BitVecVal(0, WIDTH))
    return result


def model_mask(model, coefficients):
    return sum(1 << index for index, coefficient in enumerate(coefficients)
               if z3.is_true(model.eval(coefficient, model_completion=True)))


def eval_xag(xag):
    signals = [FULL, *INPUTS]
    for node in xag["and_nodes"]:
        left = 0
        right = 0
        for index in node["left"]:
            left ^= signals[index]
        for index in node["right"]:
            right ^= signals[index]
        signals.append(left & right)
    result = 0
    for index in xag["output"]:
        result ^= signals[index]
    return result


def synthesize(target, max_and=4, timeout_ms=5000):
    for count in range(max_and + 1):
        solver = z3.Solver()
        solver.set(timeout=timeout_ms)
        node_specs = []
        signal_exprs = [z3.BitVecVal(FULL, WIDTH)] + [z3.BitVecVal(x, WIDTH) for x in INPUTS]
        for node_index in range(count):
            left_coefficients = [z3.Bool(f"a_{node_index}_{i}") for i in range(len(signal_exprs))]
            right_coefficients = [z3.Bool(f"b_{node_index}_{i}") for i in range(len(signal_exprs))]
            left = xor_selected(left_coefficients, signal_exprs)
            right = xor_selected(right_coefficients, signal_exprs)
            solver.add(z3.Or(left_coefficients), z3.Or(right_coefficients))
            signal_exprs.append(left & right)
            node_specs.append((left_coefficients, right_coefficients))
        output_coefficients = [z3.Bool(f"o_{i}") for i in range(len(signal_exprs))]
        solver.add(xor_selected(output_coefficients, signal_exprs) == z3.BitVecVal(target, WIDTH))
        result = solver.check()
        if result != z3.sat:
            print("and_count", count, "result", result, flush=True)
            continue
        model = solver.model()
        xag = {
            "and_nodes": [
                {
                    "left": [i for i in range(len(signal_exprs) - 1)
                             if model_mask(model, left) >> i & 1],
                    "right": [i for i in range(len(signal_exprs) - 1)
                              if model_mask(model, right) >> i & 1],
                }
                for left, right in node_specs
            ],
            "output": [i for i in range(len(signal_exprs))
                       if model_mask(model, output_coefficients) >> i & 1],
            "and_count": count,
            "verified": False,
        }
        if eval_xag(xag) != target:
            raise AssertionError("independent XAG verification failed")
        xag["verified"] = True
        return xag
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-and", type=int, default=4)
    parser.add_argument("--timeout-ms", type=int, default=5000)
    parser.add_argument("--output", default="artifacts/branch3_xag8_search.json")
    args = parser.parse_args()
    selector = (("x", 5), ("y", 3), ("y", 4), ("y", 5))
    table = cofactor_table(selector, 3, residual_coordinates(selector))
    target = sum(int(v) << i for i, v in enumerate(table))
    result = synthesize(target, args.max_and, args.timeout_ms)
    output = {
        "variables": 8,
        "target_hex": hex(target),
        "max_and": args.max_and,
        "timeout_ms": args.timeout_ms,
        "xag": result,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
