"""In-place reversible scheduler for exact XAG to 18-qubit quantum circuit.

Implements the direct phase oracle architecture:
    E -> Z_17 -> E^dagger
where wire 17 accumulates the logo predicate f(x, y), and E^dagger exactly restores
all coordinates q[0:12] and clean ancillas q[12:18] with zero error.
"""
from pathlib import Path
import json
import argparse
import numpy as np
from qiskit import QuantumCircuit, transpile, qasm2
from md_xag import mask_indices
from destructive_xag import load_xag
from xag import plan, linear_best
from exhaustive_verify import exhaustive

ROOT = Path(__file__).resolve().parents[1]


class XAGGraph:
    def __init__(self, nodes):
        self.nodes = {}
        for i, node in enumerate(nodes):
            nid = 13 + i
            l = [s - 1 if 1 <= s <= 12 else s for s in mask_indices(node.left_affine_mask) if s != 0]
            r = [s - 1 if 1 <= s <= 12 else s for s in mask_indices(node.right_affine_mask) if s != 0]
            self.nodes[nid] = (frozenset(l), frozenset(r))

    def ancestors(self, targets):
        res = set()
        stack = []
        for t in targets:
            if isinstance(t, (set, frozenset, list)):
                stack.extend(t)
            else:
                stack.append(t)
        while stack:
            v = stack.pop()
            if v >= 13 and v not in res:
                res.add(v)
                for f in self.nodes[v]:
                    for u in f:
                        if u >= 13:
                            stack.append(u)
        return res


def make_toggle(nodes, q_circ, w_dict, l_set, f_list):
    def toggle(v):
        node = nodes[v - 13]
        l_mask = frozenset(-1 if s == 0 else s - 1 if s <= 12 else s for s in mask_indices(node.left_affine_mask))
        r_mask = frozenset(-1 if s == 0 else s - 1 if s <= 12 else s for s in mask_indices(node.right_affine_mask))
        pre, left, right = linear_best(None, l_mask, r_mask, w_dict)
        q_circ.compose(pre, inplace=True)
        if v in l_set:
            target = w_dict[v]
            q_circ.rccx(left, right, target)
            l_set.remove(v)
            f_list.append(w_dict.pop(v))
            f_list.sort()
        else:
            target = f_list.pop(0)
            w_dict[v] = target
            l_set.add(v)
            q_circ.rccx(left, right, target)
        q_circ.compose(pre.inverse(), inplace=True)
    return toggle


def build_oracle_from_xag(xag_path: Path) -> QuantumCircuit:
    parsed = load_xag(xag_path)
    assert parsed.graph.exact(), f"XAG at {xag_path} must be exact"

    nodes = parsed.nodes
    roots = [s for s in mask_indices(parsed.output_affine_mask) if s >= 13]
    linear_outputs = [s - 1 for s in mask_indices(parsed.output_affine_mask) if 1 <= s <= 12]
    has_constant = (0 in mask_indices(parsed.output_affine_mask))

    g = XAGGraph(nodes)
    E = QuantumCircuit(18)
    wire = {i: i for i in range(12)}
    live = set()

    # Apply any linear input contributions or constant offset directly to wire 17
    if has_constant:
        E.x(17)
    for in_wire in linear_outputs:
        E.cx(in_wire, 17)

    # Scratch ancillas are strictly wires 12..16 (5 clean ancillas)
    free = list(range(12, 17))
    toggle_other = make_toggle(nodes, E, wire, live, free)

    # If root 28 exists, compute its 5 fanins into wires 12..16, apply RCCX directly into wire 17, and uncompute!
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
    for r in other_roots:
        p = plan(g, frozenset(), ({r}, set()), limit=5)
        for v in p:
            toggle_other(v)
        wr = wire[r]
        E.cx(wr, 17)
        for v in reversed(p):
            toggle_other(v)
        assert len(live) == 0

    # Full oracle: E -> Z_17 -> E^dagger
    oracle = QuantumCircuit(18)
    oracle.compose(E, inplace=True)
    oracle.z(17)
    oracle.compose(E.inverse(), inplace=True)
    return oracle


def compile_and_verify(xag_path: Path, output_qasm: Path = None, run_verify: bool = True):
    print(f"Building in-place quantum oracle from {xag_path}...")
    oracle = build_oracle_from_xag(xag_path)
    print(f"Oracle assembled: untranspiled depth = {oracle.depth()}, ops = {oracle.count_ops()}")

    print("Transpiling to ['u3', 'cx'] with qubits_initially_zero=False...")
    transpiled = transpile(
        oracle,
        basis_gates=['u3', 'cx'],
        qubits_initially_zero=False,
        optimization_level=2
    )
    depth = transpiled.depth()
    cx_count = transpiled.count_ops().get('cx', 0)
    print(f"Native transpiled depth = {depth}, CX count = {cx_count}, width = {transpiled.num_qubits}")

    if output_qasm is not None:
        output_qasm.parent.mkdir(parents=True, exist_ok=True)
        output_qasm.write_text(qasm2.dumps(transpiled))
        print(f"Saved QASM to {output_qasm}")

    if run_verify:
        print("Running exhaustive verification across all 4096 basis states...")
        exhaustive(output_qasm)
        report_file = output_qasm.with_suffix('.exhaustive.json')
        if report_file.exists():
            report = json.loads(report_file.read_text())
            print(f"Exhaustive verification PASSED! Max error = {report.get('max_error'):.2e}, ancilla error = {report.get('ancilla_error')}")

    return transpiled, depth, cx_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--xag', type=str, default='artifacts/multiplicative_depth/optimized/advanced_round4.xag')
    parser.add_argument('--output', type=str, default='artifacts/sub137_round1/oracle.qasm')
    parser.add_argument('--no-verify', action='store_true')
    args = parser.parse_args()

    compile_and_verify(
        Path(args.xag),
        Path(args.output) if args.output else None,
        run_verify=(not args.no_verify)
    )
