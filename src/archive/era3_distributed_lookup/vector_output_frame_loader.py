"""Shared ESOP loader with a persistent linear output frame.

The logical feature vector is represented as ``f = M p`` while physical
output wires ``p`` are used as dirty accumulators.  Before each cube, a cheap
linear frame transition changes M so the cube delta has one physical target.
The frame is decoded only at the end.  Relative-phase MCX is safe for this
loader when paired with its exact inverse around the complete diagonal phase
operation; the complete oracle is independently verified before acceptance.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit_aer import AerSimulator
from qiskit.synthesis import synth_mcx_n_dirty_i15, synth_mcx_noaux_v24

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows
from vector_input_basis_search import INPUT_MATRIX, INPUT_OFFSET, invert, transform_y

Y = [6 + bit for bit in range(6)]
OUT = [12 + bit for bit in range(5)]
FRAME_SEED = 1234
FRAME_SAMPLES = 2000


def rank(rows: tuple[int, ...]) -> bool:
    work = list(rows)
    found = 0
    for bit in range(5):
        pivot = next((i for i in range(found, 5) if work[i] & (1 << bit)), None)
        if pivot is None:
            continue
        work[found], work[pivot] = work[pivot], work[found]
        for i in range(5):
            if i != found and work[i] & (1 << bit):
                work[i] ^= work[found]
        found += 1
    return found == 5


def inverse5(rows: tuple[int, ...]) -> tuple[int, ...]:
    left = list(rows)
    right = [1 << i for i in range(5)]
    for bit in range(5):
        pivot = next(i for i in range(bit, 5) if left[i] & (1 << bit))
        left[bit], left[pivot] = left[pivot], left[bit]
        right[bit], right[pivot] = right[pivot], right[bit]
        for i in range(5):
            if i != bit and left[i] & (1 << bit):
                left[i] ^= left[bit]
                right[i] ^= right[bit]
    return tuple(right)


def matrix_product(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        __import__("functools").reduce(
            int.__xor__,
            (right[j] for j in range(5) if left[i] & (1 << j)),
            0,
        )
        for i in range(5)
    )


def matrix_ops(rows: tuple[int, ...]) -> list[tuple[int, int]]:
    """CNOT/SWAP row operations mapping identity to the given matrix."""
    work = list(rows)
    reduction: list[tuple[int, int]] = []
    for bit in range(5):
        pivot = next(i for i in range(bit, 5) if work[i] & (1 << bit))
        if pivot != bit:
            reduction.extend([(pivot, bit), (bit, pivot), (pivot, bit)])
            work[pivot], work[bit] = work[bit], work[pivot]
        for i in range(5):
            if i != bit and work[i] & (1 << bit):
                reduction.append((bit, i))
                work[i] ^= work[bit]
    return list(reversed(reduction))


def frame_with_first_column(mask: int, rng: random.Random) -> tuple[int, ...]:
    while True:
        columns = [mask] + [rng.randrange(1, 32) for _ in range(4)]
        rows = tuple(
            sum(((columns[column] >> row) & 1) << column for column in range(5))
            for row in range(5)
        )
        if rank(rows):
            return rows


def transformed_tables() -> dict[str, list[int]]:
    original = {name: [row[name] for row in truth_rows()] for name in FEATURES}
    inv = invert(INPUT_MATRIX)
    return {
        name: [original[name][transform_y(z, inv, INPUT_OFFSET)] for z in range(64)]
        for name in FEATURES
    }


def choose_frame(current: tuple[int, ...], mask: int,
                 rng: random.Random) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    best = None
    for _ in range(FRAME_SAMPLES):
        candidate = frame_with_first_column(mask, rng)
        transition = matrix_product(inverse5(candidate), current)
        inverse = inverse5(candidate)
        physical_delta = sum(
            ((row & mask).bit_count() & 1) << bit
            for bit, row in enumerate(inverse)
        )
        score = 2 * len(matrix_ops(transition)) + 90 * physical_delta.bit_count()
        item = (score, candidate, physical_delta, transition)
        if best is None or item[0] < best[0]:
            best = item
    _, candidate, physical_delta, transition = best
    return candidate, physical_delta, transition


def apply_output_matrix(q: QuantumCircuit, rows: tuple[int, ...]) -> None:
    for control, target in matrix_ops(rows):
        q.cx(OUT[control], OUT[target])


def apply_input_matrix(q: QuantumCircuit, rows: tuple[int, ...]) -> None:
    work = list(rows)
    # The input transform uses the same row-operation convention, but has six
    # wires and therefore cannot reuse matrix_ops above.
    reduction: list[tuple[int, int]] = []
    for bit in range(6):
        pivot = next(i for i in range(bit, 6) if work[i] & (1 << bit))
        if pivot != bit:
            reduction.extend([(pivot, bit), (bit, pivot), (pivot, bit)])
            work[pivot], work[bit] = work[bit], work[pivot]
        for i in range(6):
            if i != bit and work[i] & (1 << bit):
                reduction.append((bit, i))
                work[i] ^= work[bit]
    for control, target in reversed(reduction):
        q.cx(Y[control], Y[target])


def append_target_mcx(q: QuantumCircuit, controls: list[int], target: int) -> None:
    degree = len(controls)
    if degree == 0:
        q.x(target)
    elif degree == 1:
        q.cx(controls[0], target)
    elif degree == 2:
        q.rccx(controls[0], controls[1], target)
    elif degree == 3:
        q.compose(synth_mcx_noaux_v24(degree),
                  qubits=controls + [target], inplace=True)
    else:
        ancillas = [wire for wire in OUT if wire != target][: degree - 2]
        q.compose(synth_mcx_n_dirty_i15(degree, relative_phase=True),
                  qubits=controls + [target] + ancillas, inplace=True)


def build() -> QuantumCircuit:
    tables = transformed_tables()
    masks: defaultdict[int, list[int]] = defaultdict(list)
    for output, name in enumerate(FEATURES):
        for monomial in anf_monomials(tables[name]):
            masks[monomial].append(output)

    q = QuantumCircuit(18)
    apply_input_matrix(q, INPUT_MATRIX)
    for bit in range(6):
        if INPUT_OFFSET & (1 << bit):
            q.x(Y[bit])

    rng = random.Random(FRAME_SEED)
    current = tuple(1 << bit for bit in range(5))
    for monomial, outputs in sorted(masks.items()):
        logical_mask = sum(1 << output for output in outputs)
        next_frame, physical_delta, transition = choose_frame(current, logical_mask, rng)
        apply_output_matrix(q, transition)
        controls = [Y[bit] for bit in range(6) if monomial & (1 << bit)]
        for output in range(5):
            if physical_delta & (1 << output):
                append_target_mcx(q, controls, OUT[output])
        current = next_frame

    apply_output_matrix(q, current)
    for bit in range(6):
        if INPUT_OFFSET & (1 << bit):
            q.x(Y[bit])
    apply_input_matrix(q, invert(INPUT_MATRIX))
    return q


def verify(compiled: QuantumCircuit) -> int:
    simulator = AerSimulator(method="statevector")
    phases: list[complex] = []
    for row in truth_rows():
        circuit = QuantumCircuit(18)
        for bit in range(6):
            if (row["y"] >> bit) & 1:
                circuit.x(6 + bit)
        circuit.compose(compiled, inplace=True)
        circuit.save_statevector()
        state = simulator.run(circuit, shots=1).result().get_statevector()
        support = np.flatnonzero(np.abs(state) > 1e-7)
        if len(support) != 1:
            raise AssertionError((row["y"], "support", len(support)))
        index = int(support[0])
        actual_y = sum(((index >> (6 + bit)) & 1) << bit for bit in range(6))
        actual_out = [(index >> (12 + bit)) & 1 for bit in range(5)]
        wanted = [row[name] for name in FEATURES]
        if actual_y != row["y"] or actual_out != wanted or (index >> 17) & 1:
            raise AssertionError((row["y"], actual_y, actual_out, wanted, index))
        phases.append(complex(state[index]))
    return len({complex(round((p / abs(p)).real, 7),
                         round((p / abs(p)).imag, 7)) for p in phases})


def main() -> None:
    raw = build()
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False, optimization_level=3)
    phase_classes = verify(compiled)
    path = ARTIFACTS / "vector_output_frame_loader.qasm"
    path.write_text(qasm2.dumps(compiled))
    metrics = {
        "frame_seed": FRAME_SEED,
        "frame_samples_per_cube": FRAME_SAMPLES,
        "input_matrix_rows": list(INPUT_MATRIX),
        "input_offset": INPUT_OFFSET,
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "classical_inputs_verified": 64,
        "relative_phase_classes": phase_classes,
        "verification": "All 64 y inputs mapped to exact features with y and q17 restored.",
        "note": "Loader-only persistent output-frame diagnostic; complete-oracle integration required.",
    }
    (ARTIFACTS / "vector_output_frame_loader_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
