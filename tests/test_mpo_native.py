import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from mpo_gate_sweep import (
    initialize_gates,
    overlap,
    process_fidelity,
    project_su4,
    target_cores,
    topology_layers,
    environment,
)
from mpo_objective import process_metrics
from mpo_target import (
    DEFAULT_ORDER,
    challenge_sign_table,
    diagonal_mpo,
    mpo_basis_action,
    ordered_tensor,
    reconstruct_tt,
    tt_ranks,
    tt_svd,
)
from promote_mpo_candidate import inspect


def test_target_truth_table_and_ranks():
    signs = challenge_sign_table()
    assert signs.size == 4096
    assert np.count_nonzero(signs == -1) == 1097
    tensor = ordered_tensor(DEFAULT_ORDER)
    assert tt_ranks(tensor) == [1, 2, 4, 8, 11, 12, 11, 12, 13, 8, 4, 2, 1]


def test_tt_reconstruction_and_mpo_action():
    tensor = ordered_tensor(DEFAULT_ORDER)
    cores, _ = tt_svd(tensor)
    reconstructed = reconstruct_tt(cores)
    assert np.max(np.abs(reconstructed - tensor)) < 3e-12
    mpo = diagonal_mpo(cores)
    for bits in np.ndindex((2,) * 12):
        assert abs(mpo_basis_action(mpo, bits) - tensor[bits]) < 3e-12


def test_process_objective_identity_and_global_phase():
    identity = QuantumCircuit(12)
    baseline = process_metrics(identity)
    phased = QuantumCircuit(12)
    phased.global_phase = 0.731
    phase_metrics = process_metrics(phased)
    assert 0.21 < baseline["process_fidelity"] < 0.22
    assert abs(baseline["process_fidelity"] - phase_metrics["process_fidelity"]) < 1e-12
    assert baseline["process_infidelity"] > 0.7


def test_gate_sweep_identity_and_exact_local_improvement():
    layers = topology_layers("round_robin", 2)
    gates = initialize_gates(layers, 7, "near_identity")
    target = target_cores()
    before = process_fidelity(overlap(target, layers, gates))
    local = project_su4(environment(target, layers, gates, 0, 0))
    updated = list(gates)
    updated[0] = local
    after = process_fidelity(overlap(target, layers, updated))
    assert after > before


def test_qasm_basis_and_angle_round_trip(tmp_path):
    circuit = QuantumCircuit(12)
    circuit.u(0.123456789012345, -0.23456789012345, 0.34567890123456, 0)
    path = tmp_path / "toy.qasm"
    circuit = transpile(circuit, basis_gates=["u3", "cx"], qubits_initially_zero=False)
    path.write_text(qasm2.dumps(circuit))
    loaded = qasm2.loads(path.read_text())
    assert set(loaded.count_ops()) <= {"u3", "cx"}
    params = list(loaded.data[0].operation.params)
    assert abs(float(params[0]) - 0.123456789012345) < 1e-12


def test_promotion_precondition_inspection(tmp_path):
    circuit = QuantumCircuit(12)
    path = tmp_path / "identity.qasm"
    path.write_text(qasm2.dumps(circuit))
    report = inspect(path)
    assert report["standalone_basis_ok"]
    assert report["width_ok"]
    assert not report["promoted"]
