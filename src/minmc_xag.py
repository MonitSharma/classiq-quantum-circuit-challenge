"""Bounded exact XOR-AND synthesis for six-variable truth tables.

The solver searches XAGs with k AND nodes.  Each AND input and the final
output is an arbitrary affine XOR of the inputs, constant one, and earlier
AND nodes.  Models are verified independently using integer truth masks.
"""

import json
from pathlib import Path

import z3


FULL = (1 << 64) - 1
INPUTS = [sum(1 << row for row in range(64) if row & (1 << bit)) for bit in range(6)]


def xor_selected(coefficients, signals):
    result = z3.BitVecVal(0, 64)
    for coefficient, signal in zip(coefficients, signals):
        result = result ^ z3.If(coefficient, signal, z3.BitVecVal(0, 64))
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


def verify_xag(xag, target):
    return eval_xag(xag) == target


def synthesize_truth_table(target, max_and=6, timeout_ms=15000):
    """Return an exactly verified XAG or None when bounded search times out."""
    if target < 0 or target >= (1 << 64):
        raise ValueError("truth table must fit in 64 bits")
    for count in range(max_and + 1):
        solver = z3.Solver()
        solver.set(timeout=timeout_ms)
        node_specs = []
        signal_exprs = [z3.BitVecVal(FULL, 64)] + [z3.BitVecVal(x, 64) for x in INPUTS]
        for node_index in range(count):
            coefficients_left = [z3.Bool(f"a_{node_index}_{i}")
                                 for i in range(len(signal_exprs))]
            coefficients_right = [z3.Bool(f"b_{node_index}_{i}")
                                  for i in range(len(signal_exprs))]
            left = xor_selected(coefficients_left, signal_exprs)
            right = xor_selected(coefficients_right, signal_exprs)
            node_value = left & right
            # Avoid a syntactically empty AND input; affine constants remain
            # available through the first all-ones signal.
            solver.add(z3.Or(coefficients_left))
            solver.add(z3.Or(coefficients_right))
            signal_exprs.append(node_value)
            node_specs.append((coefficients_left, coefficients_right))

        output_coefficients = [z3.Bool(f"o_{i}") for i in range(len(signal_exprs))]
        output = xor_selected(output_coefficients, signal_exprs)
        solver.add(output == z3.BitVecVal(target, 64))
        if solver.check() != z3.sat:
            continue
        model = solver.model()
        raw_nodes = [{"left": model_mask(model, left), "right": model_mask(model, right)}
                     for left, right in node_specs]
        raw_output = model_mask(model, output_coefficients)
        # Convert masks to compact index lists and independently verify.
        xag = {"and_nodes": [
            {"left": [i for i in range(len(signal_exprs) - 1)
                      if node["left"] >> i & 1],
             "right": [i for i in range(len(signal_exprs) - 1)
                       if node["right"] >> i & 1]}
            for node in raw_nodes
        ], "output": [i for i in range(len(signal_exprs)) if raw_output >> i & 1]}
        xag["and_count"] = count
        if not verify_xag(xag, target):
            raise AssertionError("SAT model failed independent XAG verification")
        return xag
    return None


def main():
    inventory = json.loads(Path("artifacts/rank_factor_inventory.json").read_text())
    cache = {}
    for record in inventory["functions"]:
        target = record["truth_table"]
        key = str(target)
        if key not in cache:
            print("synthesizing", record["side"], target, flush=True)
            cache[key] = synthesize_truth_table(target)
    output = {"backend": "bounded_z3_xag", "timeout_ms": 15000, "functions": cache}
    Path("artifacts/minmc_factor_cache.json").write_text(json.dumps(output, indent=2))
    solved = sum(value is not None for value in cache.values())
    print(json.dumps({"functions": len(cache), "solved": solved}, indent=2))


if __name__ == "__main__":
    main()
