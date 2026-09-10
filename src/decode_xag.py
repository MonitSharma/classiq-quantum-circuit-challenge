"""XAG prototype for the class-code central decoder.

The feature lookup is kept separate from this module.  The decoder accepts
the six x bits and four class-code bits as logical inputs, computes the whole
Boolean relation into two dirty/clean work wires via reversible pebbling, and
phase-marks it with one Z before exact uncomputation.
"""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from class_oracle import build, class_tables, row_classes, codebook_binary
from formula import formula
from full_mux import multiplexer
from search import truth


class GraphN:
    def __init__(self, n):
        self.n = n
        self.full = (1 << (1 << n)) - 1
        self.inputs = [sum(1 << i for i in range(1 << n) if i >> b & 1)
                       for b in range(n)]
        self.nodes = {}
        self.tt = {i: t for i, t in enumerate(self.inputs)}
        self.basis = {}
        self.next = n
        self.insert(self.full, frozenset([-1]))
        for i, t in self.tt.items():
            self.insert(t, frozenset([i]))

    def insert(self, t, form):
        while t:
            p = t.bit_length() - 1
            if p in self.basis:
                bt, bf = self.basis[p]
                t ^= bt
                form ^= bf
            else:
                self.basis[p] = (t, form)
                return

    def lookup(self, t):
        f = frozenset()
        while t:
            p = t.bit_length() - 1
            if p not in self.basis:
                return None
            bt, bf = self.basis[p]
            t ^= bt
            f ^= bf
        return f

    def value(self, f):
        t = 0
        for v in f:
            t ^= self.full if v == -1 else self.tt[v]
        return t

    def expr(self, e):
        if isinstance(e, int):
            return frozenset([-1]) if e else frozenset()
        if e[0] == 'v':
            return frozenset([e[1]])
        a = self.expr(e[1])
        if e[0] == 'not':
            return a ^ frozenset([-1])
        b = self.expr(e[2])
        if e[0] == 'xor':
            return a ^ b
        t = self.value(a) & self.value(b)
        f = self.lookup(t)
        if f is not None and len(f - {-1}) <= 1:
            return f
        node = self.next
        self.next += 1
        self.nodes[node] = (a, b)
        self.tt[node] = t
        f = frozenset([node])
        self.insert(t, f)
        return f

    def ancestors(self, forms):
        out = {v for f in forms for v in f if v >= self.n}
        stack = list(out)
        while stack:
            v = stack.pop()
            for f in self.nodes[v]:
                for u in f:
                    if u >= self.n and u not in out:
                        out.add(u)
                        stack.append(u)
        return out


def plan(g, live, targets, limit=2, max_states=500000):
    required = frozenset(v for f in targets for v in f if v >= g.n)
    scope = g.ancestors(targets) | g.ancestors([live]) | set(live)
    ids = sorted(scope)
    pos = {v: i for i, v in enumerate(ids)}
    deps = {
        v: sum(1 << pos[u] for u in set().union(*g.nodes[v]) if u >= g.n)
        for v in ids
    }
    goal = sum(1 << pos[v] for v in required)
    start = sum(1 << pos[v] for v in live)
    ancestor_mask = sum(1 << pos[v] for v in g.ancestors(targets))

    import heapq
    def heuristic(state):
        return (ancestor_mask & ~state).bit_count() if goal else state.bit_count()

    distance = {start: 0}
    parent = {}
    queue = [(heuristic(start), 0, start)]
    while queue:
        _, cost, state = heapq.heappop(queue)
        if cost != distance.get(state):
            continue
        if ((state & goal) == goal) if goal else state == 0:
            path = []
            while state != start:
                previous, node = parent[state]
                path.append(node)
                state = previous
            return path[::-1]
        if len(distance) > max_states:
            raise ValueError('pebbling search exceeded state limit')
        width = state.bit_count()
        for node in ids:
            bit = 1 << pos[node]
            if state & deps[node] != deps[node]:
                continue
            if not state & bit and width >= limit:
                continue
            next_state = state ^ bit
            next_cost = cost + 1
            if next_cost < distance.get(next_state, 10**9):
                distance[next_state] = next_cost
                parent[next_state] = (state, node)
                heapq.heappush(queue, (next_cost + heuristic(next_state),
                                       next_cost, next_state))
    raise ValueError('decoder is not pebbleable with this limit')


def decoder_truth(codebook):
    classes, x_masks = row_classes()
    inverse = {v: i for i, v in codebook.items()}
    t = 0
    for z in range(1 << 10):
        x = z & 63
        code = z >> 6
        i = inverse.get(code)
        if i and (x_masks[i] >> x) & 1:
            t |= 1 << z
    return t


def reversible_decoder(codebook=None):
    codebook = codebook or codebook_binary()
    root_truth = decoder_truth(codebook)
    g = GraphN(10)
    root = g.expr(formula(root_truth, 10))
    # q[6] is a dirty y input that is not used by the decoder relation.  It is
    # valid workspace because the complete compute/phase/uncompute block
    # restores it; the two remaining wires are clean decoder ancillas.
    path = plan(g, frozenset(), (root,), limit=6)

    # Physical inputs are x[0:6], code[0:4] in q[12:16].  q[16:18] are the
    # only clean decoder work wires; q[6] is used as dirty workspace and is
    # restored by the inverse compute block.
    wire = {v: v for v in range(6)} | {6 + i: 12 + i for i in range(4)}
    free = list(range(6, 12)) + [16, 17]
    live = set()
    compute = QuantumCircuit(18)

    def toggle(node):
        a, b = g.nodes[node]
        forms = [set(wire[v] for v in f if v != -1) for f in (a, b)]
        const = [-1 in a, -1 in b]
        if not forms[0] or not forms[1] or forms[0] == forms[1]:
            raise ValueError('dependent decoder forms')
        p = min(forms[0] - forms[1]) if forms[0] - forms[1] else min(forms[0])
        for c in sorted(forms[0] - {p}):
            compute.cx(c, p)
            if p in forms[1]:
                if c in forms[1]:
                    forms[1].remove(c)
                else:
                    forms[1].add(c)
        r = min(forms[1] - {p})
        for c in sorted(forms[1] - {r}):
            compute.cx(c, r)
        if const[0]:
            compute.x(p)
        if const[1]:
            compute.x(r)
        target = wire.get(node)
        if target is None:
            if not free:
                raise ValueError('no decoder work wire')
            target = free.pop(0)
            wire[node] = target
        compute.rccx(p, r, target)
        if node in live:
            live.remove(node)
            free.append(target)
            free.sort()
            del wire[node]
        else:
            live.add(node)

    for node in path:
        toggle(node)
    phase_wires = [wire[v] for v in root if v >= 0]
    phase_global = any(v < 0 for v in root)
    return compute, phase_wires, phase_global


def build(codebook=None, seed=0):
    codebook = codebook or codebook_binary()
    classes, _ = row_classes()
    lookup = multiplexer(class_tables(classes, codebook, 4),
                         [12, 13, 14, 15], list(range(6, 12)), 'y', seed)
    decoder, phase_wires, phase_global = reversible_decoder(codebook)
    q = QuantumCircuit(18)
    q.compose(lookup, inplace=True)
    q.compose(decoder, inplace=True)
    if phase_global:
        q.global_phase += 3.141592653589793
    for wire in phase_wires:
        q.z(wire)
    q.compose(decoder.inverse(), inplace=True)
    q.compose(lookup.inverse(), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'],
                     qubits_initially_zero=False, optimization_level=3)


if __name__ == '__main__':
    q = build()
    Path('artifacts/class_decode_xag4.qasm').write_text(qasm2.dumps(q))
    Path('artifacts/class_decode_xag4.json').write_text(json.dumps({
        'depth': q.depth(), 'cx_count': q.count_ops().get('cx', 0)
    }, indent=2))
    print(q.depth(), q.count_ops())
