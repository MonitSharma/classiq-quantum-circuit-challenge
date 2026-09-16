"""Class-code loader built from an AND network instead of a rotation lookup.

The protected oracle loads each side's three-bit class code with
`distributed_ucry.structured_ucry`, a uniformly controlled Ry: 192 rotation slots,
78 layers, ~198 CX per block. That is the cost of an *arbitrary* six-input table.

The code is not arbitrary. `artifacts/post190_nist_catalog/{x,y}_merged_witness.json`
hold minimum-multiplicative-complexity realisations of exactly this code -- 14 AND
gates for the y side, 15 for x, both of AND depth 3 -- found from the NIST
six-variable catalogue. Each AND is a relative-phase Toffoli, whose relative phase
cancels against the uncompute because the kernel between them is diagonal.

This module compiles such a witness into a circuit and measures it. The witness
networks need three scratch wires on top of their three output wires, so a side
compiled this way occupies six ancillas; see `docs/POST185_AND_NETWORK_ROUTE.md`
for what that implies for the whole oracle.
"""
import argparse
import json
from pathlib import Path

from qiskit import QuantumCircuit, transpile



ROOT = Path(__file__).resolve().parents[1]


def load_witness(side):
    path = ROOT / ('artifacts/post190_nist_catalog/%s_merged_witness.json' % side)
    data = json.loads(path.read_text())
    return data['gates'], data['outs']


def code_table(side):
    gates, outs = load_witness(side)
    table = []
    for v in range(64):
        sig = [(v >> i) & 1 for i in range(6)]
        for g in gates:
            vals = []
            for which in ('a', 'b'):
                mask, neg = g[which]
                t = 0
                for s in mask:
                    t ^= sig[s]
                vals.append(t ^ (1 if neg else 0))
            sig.append(vals[0] & vals[1])
        code = 0
        for j, (mask, neg) in enumerate(outs):
            t = 0
            for s in mask:
                t ^= sig[s]
            code |= (t ^ (1 if neg else 0)) << j
        table.append(code)
    return table


def structure(gates, outs):
    n = len(gates)
    deps = []
    for g in gates:
        s = set()
        for which in ('a', 'b'):
            for sig in g[which][0]:
                if sig >= 6:
                    s.add(sig - 6)
        deps.append(s)
    consumers = [set() for _ in range(n)]
    for i, s in enumerate(deps):
        for u in s:
            consumers[u].add(i)
    feeds_out = [set() for _ in range(n)]
    for j, (mask, _) in enumerate(outs):
        for sig in mask:
            if sig >= 6:
                feeds_out[sig - 6].add(j)
    return deps, consumers, feeds_out


def route(a, b, wire_of, width):
    """CNOTs putting two independent affine forms onto two distinct wires.

    Same pivot enumeration as `xag.linear_best`, but on a circuit of any width:
    eliminating the first form's pivot changes the second form, so both choices
    are searched and the cheapest kept.
    """
    forms = [set(wire_of[v] for v in f if v != -1) for f in (a, b)]
    const = [-1 in a, -1 in b]
    if not forms[0] or not forms[1] or forms[0] == forms[1]:
        raise ValueError('dependent forms')
    choices = []
    for p0 in sorted(forms[0]):
        f0, f1 = set(forms[0]), set(forms[1])
        pre = QuantumCircuit(width)
        for c in sorted(f0 - {p0}):
            pre.cx(c, p0)
            if p0 in f1:
                f1.symmetric_difference_update({c})
        for r0 in sorted(f1 - {p0}):
            q = QuantumCircuit(width)
            q.compose(pre, inplace=True)
            for c in sorted(f1 - {r0}):
                q.cx(c, r0)
            if const[0]:
                q.x(p0)
            if const[1]:
                q.x(r0)
            choices.append((q, p0, r0))
    if not choices:
        raise ValueError('dependent forms')
    return min(choices, key=lambda item: (item[0].count_ops().get('cx', 0), item[0].depth()))


def forms_of(gate):
    """Both operands as signal sets, with -1 standing for the constant one."""
    out = []
    for which in ('a', 'b'):
        mask, neg = gate[which]
        f = set(mask)
        if neg:
            f.add(-1)
        out.append(frozenset(f))
    return out


def topological_orders(deps, consumers, n, tries, rng):
    """Topological orders biased towards releasing scratch early."""
    out = []
    for r in range(tries):
        rng.seed(r)
        done = set()
        order = []
        pending = {i: set(consumers[i]) for i in range(n)}
        while len(done) < n:
            ready = [i for i in range(n) if i not in done and deps[i] <= done]
            if rng.random() < 0.25:
                i = rng.choice(ready)
            else:
                scored = sorted(
                    (-sum(1 for u in deps[k] if pending[u] == {k}), len(deps[k]), k)
                    for k in ready)
                i = scored[0][2]
            order.append(i)
            done.add(i)
            for u in deps[i]:
                pending[u].discard(i)
        out.append(order)
    return out


def build_side(side, data_wires, out_wires, scratch_wires, width=18, order=None):
    """Compute the three code bits of `side` into `out_wires`.

    Scratch is a LIFO stack: a value is released, by repeating its relative-phase
    Toffoli, as soon as nothing pending needs it. Its operands are still on their
    wires because nothing below it on the stack has been released.
    """
    gates, outs = load_witness(side)
    deps, consumers, feeds_out = structure(gates, outs)
    n = len(gates)
    order = list(range(n)) if order is None else list(order)
    qc = QuantumCircuit(width)
    wire_of = {i: data_wires[i] for i in range(6)}
    pool = list(scratch_wires)
    stack = []
    pending = {i: set(consumers[i]) for i in range(n)}

    def apply_gate(i, target):
        a, b = forms_of(gates[i])
        pre, pa, pb = route(a, b, wire_of, width)
        if target in (pa, pb):
            raise ValueError('target collides with an operand pivot')
        qc.compose(pre, inplace=True)
        qc.rccx(pa, pb, target)
        qc.compose(pre.inverse(), inplace=True)

    def releasable(i):
        if pending[i]:
            return False
        # a value still on the stack will need i for its own uncompute
        for j, _ in stack:
            if j != i and i in deps[j]:
                return False
        for f in forms_of(gates[i]):
            for sig in f:
                if sig >= 0 and sig not in wire_of:
                    return False
        return True

    def release():
        changed = True
        while changed:
            changed = False
            for k in range(len(stack) - 1, -1, -1):
                i, target = stack[k]
                if not releasable(i):
                    continue
                apply_gate(i, target)
                del wire_of[6 + i]
                pool.append(target)
                stack.pop(k)
                changed = True
                break

    for i in order:
        targets = sorted(feeds_out[i])
        if not consumers[i] and len(targets) == 1:
            apply_gate(i, out_wires[targets[0]])
        else:
            if not pool:
                raise ValueError('out of scratch wires at gate %d' % i)
            target = pool.pop()
            apply_gate(i, target)
            wire_of[6 + i] = target
            stack.append((i, target))
            for j in targets:
                qc.cx(target, out_wires[j])
        for u in deps[i]:
            pending[u].discard(i)
        release()

    for j, (mask, neg) in enumerate(outs):
        for sig in mask:
            if sig < 6:
                qc.cx(data_wires[sig], out_wires[j])
        if neg:
            qc.x(out_wires[j])

    while stack:
        i, target = stack.pop()
        apply_gate(i, target)
        del wire_of[6 + i]
        pool.append(target)
    return qc


def best_side(side, data_wires, out_wires, scratch_wires, width=18, tries=400, seed=0):
    import random
    gates, outs = load_witness(side)
    deps, consumers, _ = structure(gates, outs)
    rng = random.Random(seed)
    best = None
    for order in topological_orders(deps, consumers, len(gates), tries, rng):
        try:
            qc = build_side(side, data_wires, out_wires, scratch_wires, width, order)
        except ValueError:
            continue
        native = transpile(qc, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                           optimization_level=3, seed_transpiler=0)
        key = (native.depth(), native.count_ops().get('cx', 0))
        if best is None or key < best[0]:
            best = (key, native, qc, order)
    return best


def verify(side, qc, out_wires, data_wires, width=18):
    """Check the circuit writes the code table and restores everything else.

    Takes the *logical* circuit, before transpilation: after transpiling, each
    RCCX has become rotations and no longer maps basis states to basis states.

    Basis states are tracked directly: on the computational basis RCCX acts as a
    Toffoli (its relative phase is diagonal and cancels around the diagonal
    kernel), so bit tracking is exact for this check and far cheaper than a
    statevector.
    """
    table = code_table(side)
    ops = []
    for inst in qc.data:
        name = inst.operation.name
        qubits = [qc.find_bit(v).index for v in inst.qubits]
        if name in ('cx', 'x', 'rccx', 'ccx'):
            ops.append((name, qubits))
        elif name == 'u3':
            params = [float(v) for v in inst.operation.params]
            # only X-like single-qubit gates may appear on a basis-state path
            if abs(abs(params[0]) - 3.141592653589793) < 1e-9:
                ops.append(('x', qubits))
            elif abs(params[0]) < 1e-9:
                continue
            else:
                raise AssertionError('unexpected single-qubit rotation %s' % params)
        else:
            raise AssertionError('unexpected gate %s' % name)
    for v in range(64):
        bits = [0] * width
        for i in range(6):
            bits[data_wires[i]] = (v >> i) & 1
        for name, q in ops:
            if name == 'x':
                bits[q[0]] ^= 1
            elif name == 'cx':
                bits[q[1]] ^= bits[q[0]]
            else:
                bits[q[2]] ^= bits[q[0]] & bits[q[1]]
        for i in range(6):
            assert bits[data_wires[i]] == (v >> i) & 1, ('data changed', v, i)
        code = sum(bits[out_wires[j]] << j for j in range(3))
        assert code == table[v], (v, code, table[v])
        for w in range(width):
            if w in data_wires or w in out_wires:
                continue
            assert bits[w] == 0, ('dirty scratch', v, w)
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--side', choices=['y', 'x'], default='y')
    p.add_argument('--scratch', type=int, default=5)
    p.add_argument('--tries', type=int, default=300)
    a = p.parse_args()
    # standalone component: six address wires, three outputs, then scratch
    data = list(range(6))
    outs = [6, 7, 8]
    scratch = list(range(9, 9 + a.scratch))
    width = 9 + a.scratch
    best = best_side(a.side, data, outs, scratch, width=width, tries=a.tries)
    if best is None:
        raise SystemExit('no schedule fits %d scratch wires' % a.scratch)
    (depth, cx), native, logical, order = best
    verify(a.side, logical, outs, data, width=width)
    print(json.dumps(dict(side=a.side, scratch=a.scratch, width=width,
                          depth=depth, cx=cx,
                          and_gates=len(load_witness(a.side)[0]), order=order)))
