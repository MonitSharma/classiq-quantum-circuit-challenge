"""Direct reversible Shannon evaluator for the documented BDD order."""

from pathlib import Path

from pyeda.inter import BinaryDecisionDiagram, expr2bdd, exprvars, truthtable, truthtable2expr
from qiskit import QuantumCircuit, qasm2, transpile

from search import logo

ORDER = [0, 1, 5, 2, 3, 4, 11, 10, 9, 8, 6, 7]


def target_values():
    values = []
    for assignment in __import__("itertools").product((0, 1), repeat=12):
        q = [0] * 12
        for i, bit in enumerate(assignment):
            q[ORDER[i]] = bit
        x = sum(q[i] << i for i in range(6))
        y = sum(q[6 + i] << i for i in range(6))
        values.append(int(logo(x, y)))
    return values


def eval_bdd(q, node, target, free):
    """Compute node into target, preserving inputs and free scratch."""
    if node.root == -1:
        return
    if node.root == -2:
        q.x(target)
        return
    if not free:
        raise ValueError("insufficient clean ancillas for BDD node")
    lo = BinaryDecisionDiagram(node.lo)
    hi = BinaryDecisionDiagram(node.hi)
    delta = lo ^ hi
    eval_bdd(q, lo.node, target, free)
    aux = free[0]
    eval_bdd(q, delta.node, aux, free[1:])
    variable = ORDER[node.root - 1]
    q.ccx(variable, aux, target)
    eval_bdd(q, delta.node, aux, free[1:])


def build():
    variables = exprvars("bdd", 12)
    bdd = expr2bdd(truthtable2expr(truthtable(variables, target_values())))
    q = QuantumCircuit(18)
    eval_bdd(q, bdd.node, 12, [13, 14, 15, 16, 17])
    q.z(12)
    inverse = q.inverse()
    q.compose(inverse, inplace=True)
    return q


if __name__ == "__main__":
    circuit = transpile(build(), basis_gates=["u3", "cx"],
                        qubits_initially_zero=False, optimization_level=3)
    print("depth", circuit.depth(), "cx", circuit.count_ops().get("cx", 0),
          "width", circuit.num_qubits, flush=True)
    Path("artifacts/bdd_reversible.qasm").write_text(qasm2.dumps(circuit))

