"""Test continuous in-place reversible pebbler and verify depth."""
from pathlib import Path
import json
from qiskit import QuantumCircuit, transpile, qasm2
from md_xag import mask_indices
from destructive_xag import load_xag
from xag import plan, linear_best
from xag_to_inplace_layers import XAGGraph, make_toggle
from exhaustive_verify import exhaustive

xag_path = Path("artifacts/multiplicative_depth/optimized/advanced_round4.xag")
parsed = load_xag(xag_path)
nodes = parsed.nodes
roots = [s for s in mask_indices(parsed.output_affine_mask) if s >= 13]
linear_outputs = [s - 1 for s in mask_indices(parsed.output_affine_mask) if 1 <= s <= 12]
has_constant = (0 in mask_indices(parsed.output_affine_mask))

g = XAGGraph(nodes)
E = QuantumCircuit(18)
wire = {i: i for i in range(12)}
live = set()

if has_constant:
    E.x(17)
for in_wire in linear_outputs:
    E.cx(in_wire, 17)

free = list(range(12, 17))
toggle_other = make_toggle(nodes, E, wire, live, free)

other_roots = list(roots)
if 28 in roots:
    other_roots.remove(28)
    p28 = plan(g, frozenset(), ({17, 18, 25, 26, 27}, set()), limit=5)
    for v in p28:
        toggle_other(v)
    node28 = nodes[28 - 13]
    l28_mask = frozenset(-1 if s == 0 else s - 1 if s <= 12 else s for s in mask_indices(node28.left_affine_mask))
    r28_mask = frozenset(-1 if s == 0 else s - 1 if s <= 12 else s for s in mask_indices(node28.right_affine_mask))
    pre28, left28, right28 = linear_best(None, l28_mask, r28_mask, wire)
    E.compose(pre28, inplace=True)
    E.rccx(left28, right28, 17)
    E.compose(pre28.inverse(), inplace=True)
    for v in reversed(p28):
        toggle_other(v)
    assert len(live) == 0
    assert free == list(range(12, 17))

# Continuous pebbling across other_roots!
for r in other_roots:
    if r not in live:
        p = plan(g, frozenset(live), ({r}, set()), limit=5)
        for v in p:
            toggle_other(v)
    assert r in live
    wr = wire[r]
    E.cx(wr, 17)

# Clean up all remaining live pebbles to empty set
p_clean = plan(g, frozenset(live), (set(), set()), limit=5)
for v in p_clean:
    toggle_other(v)
assert len(live) == 0
assert free == list(range(12, 17))

# Full oracle: E -> Z_17 -> E^dagger
oracle = QuantumCircuit(18)
oracle.compose(E, inplace=True)
oracle.z(17)
oracle.compose(E.inverse(), inplace=True)

print("Oracle built! Transpiling...")
transpiled = transpile(
    oracle,
    basis_gates=['u3', 'cx'],
    qubits_initially_zero=False,
    optimization_level=3
)
depth = transpiled.depth()
cx_count = transpiled.count_ops().get('cx', 0)
print(f"Transpiled depth = {depth}, CX count = {cx_count}")

out_path = Path("artifacts/sub137_round1/oracle_continuous.qasm")
out_path.write_text(qasm2.dumps(transpiled))
print(f"Saved to {out_path}")

print("Running exhaustive verification...")
exhaustive(out_path)
report_file = out_path.with_suffix('.exhaustive.json')
if report_file.exists():
    report = json.loads(report_file.read_text())
    print(f"VERIFICATION: max_error = {report.get('max_error'):.2e}, ancilla_error = {report.get('ancilla_error')}")
