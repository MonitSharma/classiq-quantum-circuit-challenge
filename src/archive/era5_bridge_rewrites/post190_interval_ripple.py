"""Disk interval phase by a single modular ripple, with no threshold register.

The dyadic and MCX-threshold blocks both materialise c +/- t in a five-bit
register, which needs wide multi-controlled gates with no clean helper left.
Here the window test is folded into one modular add and one four-majority
comparison:

    r = (v + t + K) mod 32,  K = (1 - c) mod 32 = 8 + 6*(1-y5) + 16*y5
    window  <=>  r <= 2t+2  <=>  not (r >= 2(t+1)+1)

so the only register ever formed is t+1, on the radius wires themselves.
"""
import functools, json
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native
from post190_y_fold import mcx

V = [6, 7, 8, 9, 10]
Y5 = 11
T = [12, 13, 14]
C, R, F = 15, 16, 17          # carry helper / compare result / guard flag


def maj(q, c, b, a):
    q.cx(a, b); q.cx(a, c); q.ccx(c, b, a)


def uma(q, c, b, a):
    q.ccx(c, b, a); q.cx(a, c); q.cx(c, b)


def add_t(q):
    """v += t  (mod 32); C is a clean carry-in and is restored."""
    maj(q, C, V[0], T[0]); maj(q, T[0], V[1], T[1]); maj(q, T[1], V[2], T[2])
    q.ccx(T[2], V[3], V[4]); q.cx(T[2], V[3])        # carry into the top two bits
    uma(q, T[1], V[2], T[2]); uma(q, T[0], V[1], T[1]); uma(q, C, V[0], T[0])


def add_k(q, helpers=(C, R)):
    """v += 8 + 6*(1-y5) + 16*y5  (mod 32)."""
    q.cx(Y5, V[4])                                    # + 16*y5
    q.cx(V[3], V[4]); q.x(V[3])                       # + 8
    q.x(Y5)                                           # g = not y5
    mcx(q, [Y5, V[2], V[3]], V[4], helpers); mcx(q, [Y5, V[2]], V[3], helpers)
    q.cx(Y5, V[2])                                    # + 4*g
    mcx(q, [Y5, V[1], V[2], V[3]], V[4], helpers); mcx(q, [Y5, V[1], V[2]], V[3], helpers)
    mcx(q, [Y5, V[1]], V[2], helpers); q.cx(Y5, V[1])  # + 2*g
    q.x(Y5)


def inc_t(q, helpers=(R,)):
    """radius wires become t+1 on four bits T[0],T[1],T[2],C."""
    mcx(q, T, C, helpers)
    q.ccx(T[0], T[1], T[2]); q.cx(T[0], T[1]); q.x(T[0])


def compare(q):
    """R ^= [ r >= 2*(t+1)+1 ], via carry-out of r + ~B + 1 with B = 2(t+1)+1."""
    q.x(T + [C])
    chain = QuantumCircuit(18)
    maj(chain, V[0], V[1], T[0]); maj(chain, T[0], V[2], T[1])
    maj(chain, T[1], V[3], T[2]); maj(chain, T[2], V[4], C)
    q.compose(chain, inplace=True); q.cx(C, R); q.compose(chain.inverse(), inplace=True)
    q.x(T + [C])


def guard(q, helpers=(C, R)):
    """F ^= x5 and (t != 0)."""
    q.cx(5, F); q.x(T); mcx(q, [5] + T, F, helpers); q.x(T)


def raw_interval():
    q = QuantumCircuit(18)
    guard(q)
    add_t(q); add_k(q); inc_t(q)
    compare(q)
    q.x(R); q.cz(R, F); q.x(R)
    compare(q)
    inv = QuantumCircuit(18); add_t(inv); add_k(inv); inc_t(inv)
    q.compose(inv.inverse(), inplace=True)
    g = QuantumCircuit(18); guard(g); q.compose(g.inverse(), inplace=True)
    return q


def interval_phase():
    return native(raw_interval())


def predicate(x, y):
    from post190_radius_interval import make_lookup, folded
    _, vals, _ = _lookup()
    b = y >> 5; m, s = folded(x | (b << 6)); t = vals[m | (s << 4) | (b << 5)]
    c = 19 if not b else 9
    return bool(x & 32) and t != 0 and c - t - 1 <= (y & 31) <= c + t + 1


@functools.lru_cache(None)
def _lookup():
    from post190_radius_interval import make_lookup
    return make_lookup()


def simulate(q, state):
    """Classical reversible simulation for x/cx/ccx/rccx circuits."""
    for inst in q.data:
        n = inst.operation.name; w = [q.find_bit(b).index for b in inst.qubits]
        if n == 'x': state ^= 1 << w[0]
        elif n == 'cx':
            if state >> w[0] & 1: state ^= 1 << w[1]
        elif n in ('ccx', 'rccx'):
            if (state >> w[0] & 1) and (state >> w[1] & 1): state ^= 1 << w[2]
        elif n in ('cz', 'z', 'h', 'u', 'u3', 'p', 'rz'): pass
        else: raise AssertionError(n)
    return state


def check():
    """Every classical block is exercised on all 64*8*2 relevant assignments."""
    body = QuantumCircuit(18)
    add_t(body); add_k(body); inc_t(body)
    bad = 0
    for v in range(32):
        for t in range(8):
            for y5 in (0, 1):
                s = (v << 6) | (y5 << 11) | (t << 12)
                out = simulate(body, s)
                r = (out >> 6) & 31; u = ((out >> 12) & 7) | ((out >> 15 & 1) << 3)
                want_r = (v + t + (14 if not y5 else 24)) % 32
                if r != want_r or u != t + 1 or (out >> 16): bad += 1
    return bad


def run(out):
    from qiskit import qasm2
    from post190_radius_interval import make_lookup, rectangle_phase
    assert not out.exists(); out.mkdir(parents=True)
    assert check() == 0
    lookup, values, lr = make_lookup()
    e = QuantumCircuit(18)
    for i in range(5): e.cx(11, i)
    e.x(3); e.cx(3, 4)
    for i in range(4): e.cx(4, i)
    e.compose(lookup, [0, 1, 2, 3, 4, 11, 12, 13, 14], inplace=True); e = native(e)
    k = interval_phase()
    rect, _ = rectangle_phase()
    disk = native(e.compose(k).compose(e.inverse()))
    full = native(rect.compose(disk))
    for name, c in [('interval', k), ('disk', disk), ('oracle', full)]:
        (out / (name + '.qasm')).write_text(qasm2.dumps(c))
    from exhaustive_verify import exhaustive
    exhaustive(out / 'oracle.qasm')
    r = dict(lookup=lr, encoder_depth=e.depth(), interval_depth=k.depth(),
             interval_cx=k.count_ops().get('cx', 0), rectangle_depth=rect.depth(),
             rectangle_cx=rect.count_ops().get('cx', 0), disk_depth=disk.depth(),
             depth=full.depth(), cx=full.count_ops().get('cx', 0), width=18)
    (out / 'report.json').write_text(json.dumps(r, indent=2)); print(r, flush=True)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--outdir', required=True, type=Path)
    run(p.parse_args().outdir)
