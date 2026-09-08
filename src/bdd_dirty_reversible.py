"""BDD Shannon evaluator using corrected dirty-input workspaces."""

from functools import lru_cache
from pathlib import Path
import itertools

from pyeda.inter import BinaryDecisionDiagram, expr2bdd, exprvars, truthtable, truthtable2expr
from qiskit import QuantumCircuit, qasm2, transpile

from search import logo

ORDER = [0, 1, 5, 2, 3, 4, 11, 10, 9, 8, 6, 7]


def target_values():
    values = []
    for assignment in itertools.product((0, 1), repeat=12):
        q = [0] * 12
        for i, bit in enumerate(assignment):
            q[ORDER[i]] = bit
        x = sum(q[i] << i for i in range(6))
        y = sum(q[6 + i] << i for i in range(6))
        values.append(int(logo(x, y)))
    return values


@lru_cache(None)
def support(node_id, root, lo_id, hi_id):
    if root < 0:
        return frozenset()
    lo = _nodes[lo_id]
    hi = _nodes[hi_id]
    return frozenset((ORDER[root - 1],)) | support(id(lo), lo.root, id(lo.lo), id(lo.hi)) | support(id(hi), hi.root, id(hi.lo), id(hi.hi))


_nodes = {}


def node_support(node):
    if node.root < 0:
        return frozenset()
    _nodes[id(node)] = node
    _nodes[id(node.lo)] = node.lo
    _nodes[id(node.hi)] = node.hi
    return frozenset((ORDER[node.root - 1],)) | node_support(node.lo) | node_support(node.hi)


def eval_toggle(q, node, target, free, busy):
    """Toggle target by node's Boolean value, allowing corrected dirty aux."""
    if node.root == -1:
        return
    if node.root == -2:
        q.x(target)
        return
    lo = BinaryDecisionDiagram(node.lo)
    hi = BinaryDecisionDiagram(node.hi)
    delta = lo ^ hi
    variable = ORDER[node.root - 1]
    eval_toggle(q, lo.node, target, free, busy)

    delta_support = node_support(delta.node)
    candidates = [wire for wire in free if wire not in delta_support and wire != variable]
    if candidates:
        aux = candidates[0]
        next_free = [wire for wire in free if wire != aux]
        eval_toggle(q, delta.node, aux, next_free, busy | ({aux} if aux < 12 else set()))
        q.ccx(variable, aux, target)
        eval_toggle(q, delta.node, aux, next_free, busy | ({aux} if aux < 12 else set()))
        q.ccx(variable, aux, target)
        return

    dirty = [wire for wire in range(12)
             if wire not in delta_support and wire != variable and wire != target and wire not in busy]
    if not dirty:
        raise ValueError("insufficient clean and dirty workspace for BDD node")
    aux = dirty[0]
    eval_toggle(q, delta.node, aux, free, busy | {aux})
    q.ccx(variable, aux, target)
    eval_toggle(q, delta.node, aux, free, busy | {aux})
    q.ccx(variable, aux, target)


def build():
    variables = exprvars("bdd_dirty", 12)
    bdd = expr2bdd(truthtable2expr(truthtable(variables, target_values())))
    node_support(bdd.node)
    q = QuantumCircuit(18)
    eval_toggle(q, bdd.node, 12, [13, 14, 15, 16, 17], set())
    q.z(12)
    q.compose(q.inverse(), inplace=True)
    return q


if __name__ == "__main__":
    circuit = transpile(build(), basis_gates=["u3", "cx"],
                        qubits_initially_zero=False, optimization_level=3)
    print("depth", circuit.depth(), "cx", circuit.count_ops().get("cx", 0),
          "width", circuit.num_qubits, flush=True)
    Path("artifacts/bdd_dirty_reversible.qasm").write_text(qasm2.dumps(circuit))

