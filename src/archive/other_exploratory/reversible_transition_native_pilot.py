"""Measure native synthesis of one exact controlled state permutation.

This is a diagnostic only.  It deliberately does not emit QASM or alter the
protected oracle artifacts.  The permutation comes from the exact semantic
width-limited model; basis-state swaps are routed through Gray paths and each
neighbor swap is implemented as a multi-controlled X.
"""

from __future__ import annotations

import argparse
import warnings

from qiskit import QuantumCircuit, transpile

from reversible_width256_synthesis import build_model


NATIVE_ORDER = (11, 9, 10, 5, 4, 2, 3, 1, 0, 8, 7, 6)


def gray_path_swaps(a: int, b: int) -> list[tuple[int, int]]:
    path = [a]
    current = a
    difference = a ^ b
    while difference:
        bit = difference & -difference
        current ^= bit
        path.append(current)
        difference ^= bit
    return ([(path[i], path[i + 1]) for i in range(len(path) - 1)] +
            [(path[i], path[i + 1]) for i in range(len(path) - 3, -1, -1)])


def cycle_transpositions(permutation: list[int]) -> list[tuple[int, int]]:
    seen = [False] * len(permutation)
    result = []
    for start in range(len(permutation)):
        if seen[start]:
            continue
        cycle = []
        current = start
        while not seen[current]:
            seen[current] = True
            cycle.append(current)
            current = permutation[current]
        result.extend((cycle[0], value) for value in cycle[1:])
    return result


def build_native_pilot(permutation: list[int], branch: int,
                       mode: str = "v-chain") -> QuantumCircuit:
    state_bits = 7
    # Seven state bits plus one branch control plus six clean MCX work wires.
    circuit = QuantumCircuit(14)
    ancillas = list(range(8, 14))
    for first, second in cycle_transpositions(permutation):
        for a, b in gray_path_swaps(first, second):
            difference = a ^ b
            target = (difference & -difference).bit_length() - 1
            controls = [wire for wire in range(state_bits) if wire != target]
            controls.append(7)
            for wire in range(state_bits):
                if wire != target and not ((a >> wire) & 1):
                    circuit.x(wire)
            kwargs = {"mode": mode}
            if mode != "noancilla":
                kwargs["ancilla_qubits"] = ancillas
            circuit.mcx(controls, target, **kwargs)
            for wire in range(state_bits):
                if wire != target and not ((a >> wire) & 1):
                    circuit.x(wire)
    return circuit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", type=int, default=6)
    parser.add_argument("--branch", type=int, choices=(0, 1), default=1)
    parser.add_argument("--label-seed", type=int, default=43)
    parser.add_argument("--mode", choices=("v-chain", "v-chain-dirty", "recursion", "noancilla"),
                        default="v-chain")
    args = parser.parse_args()
    if not 6 <= args.layer < 12:
        raise SystemExit("--layer must be in 6..11")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = build_model(NATIVE_ORDER, state_bits=7, output_parity=False,
                            label_seed=args.label_seed)
        permutation = model["layers"][args.layer - 6]["permutations"][args.branch]
        circuit = build_native_pilot(permutation, args.branch, args.mode)
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False,
                             optimization_level=3)
    print({
        "status": "native transition pilot; not a complete classifier",
        "layer": args.layer,
        "branch": args.branch,
        "label_seed": args.label_seed,
        "mcx_mode": args.mode,
        "cycle_transpositions": len(cycle_transpositions(permutation)),
        "gray_neighbor_swaps": sum(
            len(gray_path_swaps(a, b))
            for a, b in cycle_transpositions(permutation)
        ),
        "compiled_depth": compiled.depth(),
        "compiled_cx": compiled.count_ops().get("cx", 0),
        "qubits": compiled.num_qubits,
    })


if __name__ == "__main__":
    main()
