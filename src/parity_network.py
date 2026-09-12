"""Depth-aware parity network for a diagonal phase polynomial.

Given a phase function on n wires expanded in the Walsh basis, apply Rz on each
nonzero parity.  The wires themselves are the only hosts available, so a wire
that has been CX'd into no longer holds its original value; the linear state is
tracked explicitly, which is what makes this correct.  Moves are chosen greedily
and packed into layers of disjoint CX gates so the result is shallow rather than
CX-minimal.
"""
import numpy as np
from qiskit import QuantumCircuit


def walsh(values):
    a = np.array(values, dtype=float)
    n = len(a)
    h = 1
    while h < n:
        for i in range(0, n, 2 * h):
            lo = a[i:i + h].copy()
            hi = a[i + h:i + 2 * h].copy()
            a[i:i + h] = lo + hi
            a[i + h:i + 2 * h] = lo - hi
        h *= 2
    return a / n


def _solve(states, target, n):
    """Subset of wire indices whose parities XOR to `target`, or None."""
    piv = {}
    for j in range(n):
        v, comb = states[j], frozenset([j])
        for b in range(n - 1, -1, -1):
            if v >> b & 1:
                if b in piv:
                    pv, pc = piv[b]
                    v ^= pv
                    comb = comb ^ pc
                else:
                    piv[b] = (v, comb)
                    break
    v, comb = target, frozenset()
    for b in range(n - 1, -1, -1):
        if v >> b & 1:
            if b not in piv:
                return None
            pv, pc = piv[b]
            v ^= pv
            comb = comb ^ pc
    return comb if v == 0 else None


def synth(phase_values, n, tol=1e-12):
    """Circuit applying exp(i*phase_values[w]) to |w>, up to a global phase.

    The wires are the only hosts, so a wire that has been CX'd into no longer
    holds its original value.  The linear state is tracked explicitly and each
    parity is reached by solving for it in the CURRENT basis, choosing a host
    that appears in the solution so the move is always one round of CX gates.
    Rounds use disjoint wire pairs, which keeps the result shallow.
    """
    coeff = walsh(phase_values)
    remaining = {m: float(coeff[m]) for m in range(1, 1 << n) if abs(coeff[m]) > tol}
    qc = QuantumCircuit(n)
    states = [1 << j for j in range(n)]
    # give each wire its own queue so several can advance per layer
    queue = {j: [] for j in range(n)}
    for m in sorted(remaining, key=lambda z: (bin(z).count('1'), z)):
        host = min((j for j in range(n) if m >> j & 1),
                   key=lambda j: (len(queue[j]), j))
        queue[host].append(m)
    guard = 0
    while remaining:
        guard += 1
        if guard > 50000:
            raise RuntimeError('parity walk did not terminate')
        for j in range(n):
            if states[j] in remaining:
                qc.rz(-2 * remaining.pop(states[j]), j)
                if states[j] in queue[j]:
                    queue[j].remove(states[j])
        if not remaining:
            break
        busy = set()
        moved = False
        for j in range(n):
            if j in busy:
                continue
            targets = queue[j] or list(remaining)
            pick = None
            for m in targets:
                comb = _solve(states, m, n)
                if comb is None or j not in comb:
                    continue
                rest = [k for k in comb if k != j and k not in busy]
                if len(rest) == len(comb) - 1 or rest:
                    pick = (m, rest)
                    break
            if pick is None or not pick[1]:
                continue
            k = pick[1][0]
            qc.cx(k, j)
            states[j] ^= states[k]
            busy.add(j)
            busy.add(k)
            moved = True
        if not moved:
            # fall back to a single serial move on the cheapest parity
            best = None
            for m in remaining:
                comb = _solve(states, m, n)
                if comb is None:
                    continue
                for host in comb:
                    if best is None or len(comb) < best[0]:
                        best = (len(comb), m, host, comb)
            if best is None:
                raise RuntimeError('no reachable parity')
            _, m, host, comb = best
            for k in sorted(comb):
                if k != host:
                    qc.cx(k, host)
                    states[host] ^= states[k]
    qc.compose(restore(states, n), inplace=True)
    return qc


def restore(state, n):
    """CX circuit returning wires holding `state` parities back to the identity."""
    rows = [state[j] for j in range(n)]
    qc = QuantumCircuit(n)
    for col in range(n):
        piv = next((r for r in range(col, n) if rows[r] >> col & 1), None)
        if piv is None:
            raise ValueError('linear state is singular')
        if piv != col:
            for a, b in ((piv, col), (col, piv), (piv, col)):
                qc.cx(a, b)
                rows[b] ^= rows[a]
        for r in range(n):
            if r != col and rows[r] >> col & 1:
                qc.cx(col, r)
                rows[r] ^= rows[col]
    assert rows == [1 << j for j in range(n)], rows
    return qc
