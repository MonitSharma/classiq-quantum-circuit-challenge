"""Bounded SAT synthesis for chain-shaped, three-slot-friendly XAGs.

Each AND node may use an arbitrary affine form of the six inputs and the
immediately preceding AND node.  The output is an affine form of the inputs
and the final node.  This is deliberately narrower than a general XAG, but
its dependency shape admits compute/clear with an output plus two scratch
wires.
"""

import json
from pathlib import Path

import z3

from minmc_xag import FULL, INPUTS, verify_xag


def xor_selected(coefficients, signals):
    value = z3.BitVecVal(0, 64)
    for coefficient, signal in zip(coefficients, signals):
        value ^= z3.If(coefficient, signal, z3.BitVecVal(0, 64))
    return value


def mask(model, coefficients):
    return sum(1 << i for i, c in enumerate(coefficients)
               if z3.is_true(model.eval(c, model_completion=True)))


def synthesize(target, max_and=8, timeout_ms=3000):
    for count in range(1, max_and + 1):
        solver = z3.Solver()
        solver.set(timeout=timeout_ms)
        signals = [z3.BitVecVal(FULL, 64),
                   *[z3.BitVecVal(value, 64) for value in INPUTS]]
        specs = []
        for node in range(count):
            # constant + six inputs + immediately previous AND, if present
            available = signals[:7] if node == 0 else signals[:7] + [signals[-1]]
            left_c = [z3.Bool(f"l_{node}_{i}") for i in range(len(available))]
            right_c = [z3.Bool(f"r_{node}_{i}") for i in range(len(available))]
            solver.add(z3.Or(left_c), z3.Or(right_c))
            signals.append(xor_selected(left_c, available) & xor_selected(right_c, available))
            specs.append((left_c, right_c))
        available = signals[:7] + [signals[-1]]
        output_c = [z3.Bool(f"o_{i}") for i in range(len(available))]
        solver.add(xor_selected(output_c, available) == z3.BitVecVal(target, 64))
        if solver.check() != z3.sat:
            continue
        nodes = []
        for node, (left_c, right_c) in enumerate(specs):
            previous = 7 + node - 1
            def remap(value_mask):
                return [i if i < 7 else previous for i in range(8)
                        if value_mask >> i & 1]
            nodes.append({"left": remap(mask(solver.model(), left_c)),
                          "right": remap(mask(solver.model(), right_c))})
        out_mask = mask(solver.model(), output_c)
        final_node = 7 + count - 1
        xag = {"and_nodes": nodes,
               "output": [i if i < 7 else final_node for i in range(8)
                          if out_mask >> i & 1],
               "and_count": count}
        if not verify_xag(xag, target):
            raise AssertionError("chain model failed independent verification")
        return xag
    return None


def main():
    inventory = json.loads(Path("artifacts/rank_factor_inventory.json").read_text())
    targets = sorted({record["truth_table"] for record in inventory["functions"]})
    cache = {}
    for target in targets:
        print("synthesizing chain", target, flush=True)
        cache[str(target)] = synthesize(target)
    Path("artifacts/pebble_xag_cache.json").write_text(json.dumps({
        "backend": "bounded_z3_chain_xag", "max_and": 8,
        "timeout_ms_per_bound": 3000, "functions": cache}, indent=2))
    print(json.dumps({"functions": len(cache),
                      "solved": sum(value is not None for value in cache.values())}, indent=2))


if __name__ == "__main__":
    main()
