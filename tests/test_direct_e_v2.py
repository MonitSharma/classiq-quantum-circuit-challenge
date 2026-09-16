import random

import numpy as np
import pytest
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

from direct_e_v2 import (
    ALL_ONES, TARGET, assemble, depth_ceiling, layout, margolus, mutate,
    nearest_affine, parity, semantic, solve_layers, validate,
)
from destructive_semantic_search import exact_affine_distance, initial_wire_truth_tables
from direct_e_affine_seed import screen
from distributed_frame_search import native


def test_margolus_full_unitary_and_existing_rccx_cost():
    u = Operator(margolus()).data
    ccx = QuantumCircuit(3)
    ccx.ccx(0, 1, 2)
    assert np.allclose(abs(u), abs(Operator(ccx).data), atol=1e-14)
    assert margolus().depth() == 7
    assert margolus().count_ops() == {'u3': 4, 'cx': 3}
    old = QuantumCircuit(3)
    old.rccx(0, 1, 2)
    assert native(old).depth() == 7  # Not a new saving over the old compiler.


def test_nearest_affine_agrees_with_exhaustive_parity_enumeration():
    rng = random.Random(185)
    wires = tuple(rng.getrandbits(4096) for _ in range(18))
    result = nearest_affine(wires)
    old_distance, _ = exact_affine_distance(wires)
    assert result['distance'] == old_distance
    assert (parity(wires, result['mask'], result['constant']) ^ TARGET).bit_count() == old_distance


def test_nearest_affine_finds_high_weight_mask_and_constant():
    wires = initial_wire_truth_tables()
    mask = sum(1 << i for i in range(10))
    target = parity(wires, mask, 1)
    fit = nearest_affine(wires, target)
    assert fit['distance'] == 0
    assert parity(wires, fit['mask'], fit['constant']) == target
    assert nearest_affine((0,) * 18, ALL_ONES)['constant'] == 1


def test_serialized_literal_inverse_with_dirty_targets_and_parallel_phase():
    layers = [
        {'kind': 'cx', 'gates': [[0, 12]]},
        {'kind': 'ccx', 'gates': [[12, 1, 2]]},
        {'kind': 'ccx', 'gates': [[2, 3, 13]]},
    ]
    q = qasm2.loads(qasm2.dumps(assemble(layers, (1 << 12) | (1 << 13), 1)))
    used = [0, 1, 2, 3, 12, 13]
    small = QuantumCircuit(len(used))
    for inst in q.data:
        small.append(inst.operation, [used.index(q.find_bit(w).index) for w in inst.qubits])
    expected = []
    for x in range(1 << len(used)):
        word = sum(((x >> i) & 1) << w for i, w in enumerate(used))
        for layer in layers:
            for g in layer['gates']:
                if len(g) == 2:
                    word ^= ((word >> g[0]) & 1) << g[1]
                else:
                    word ^= (((word >> g[0]) & 1) & ((word >> g[1]) & 1)) << g[2]
        expected.append((-1) ** (((word >> 12) ^ (word >> 13)) & 1))
    assert np.allclose(Operator(small).data, np.diag(expected), atol=1e-13)
    assert q.depth() <= depth_ceiling(layers)


def test_mutations_preserve_physical_matchings_and_budgets():
    rng = random.Random(7)
    layers = layout(7, 18)
    for _ in range(200):
        layers = mutate(layers, rng)
        validate(layers)
    assert sum(x['kind'] == 'ccx' for x in layers) == 7
    assert sum(x['kind'] == 'cx' for x in layers) == 18
    assert depth_ceiling(layers) <= 135
    with pytest.raises(AssertionError):
        validate([{'kind': 'cx', 'gates': [[0, 1], [1, 2]]}])


def test_sat_parallel_phase_mask_positive_control():
    layers = [{'kind': 'ccx', 'gates': [[0, 1, 12], [2, 3, 13]]}]
    wires = semantic(layers)
    target = wires[12] ^ wires[13] ^ ALL_ONES
    result = solve_layers(layers, set(), list(range(4096)), target, seconds=5)
    assert result['status'] == 'sat'
    assert result['distance'] == 0
    assert (result['mask'] & ((1 << 12) | (1 << 13))) == (1 << 12) | (1 << 13)
    assert result['constant'] == 1


def test_free_first_layer_positive_control_and_replay():
    wires = initial_wire_truth_tables()
    target = wires[7] & wires[10]
    samples = random.Random(17).sample(range(4096), 96)
    result = solve_layers([{'kind': 'ccx', 'gates': []}], {0}, samples, target, seconds=20)
    assert result['status'] == 'sat'
    assert result['distance'] == 0


def test_identity_cannot_satisfy_nonlinear_target():
    wires = initial_wire_truth_tables()
    result = solve_layers([], set(), list(range(32)), wires[0] & wires[1], seconds=5)
    assert result['status'] == 'unsat'


def test_affine_seed_reproduces_claim_and_physical_inverse():
    result = screen()
    assert result['identity_terms'] == 886
    assert result['terms'] == 264
    assert len(result['substitution_ops']) == 10
    layers = [{'kind': op[0], 'gates': [list(op[1:])]} for op in result['substitution_ops']]
    wires = semantic(layers)
    for x in range(4096):
        encoded = sum(((wires[i] >> x) & 1) << i for i in range(12))
        assert result['mapping_old_input_for_new_coordinate'][encoded] == x
    q = assemble(layers, 1 << 2)
    assert set(q.count_ops()) <= {'u3', 'cx'}


def test_sat_free_x_layer_positive_control():
    wires = initial_wire_truth_tables()
    result = solve_layers([{'kind': 'x', 'gates': []}], {0}, list(range(4096)), wires[1] ^ ALL_ONES, seconds=5)
    assert result['status'] == 'sat'
    assert result['distance'] == 0
