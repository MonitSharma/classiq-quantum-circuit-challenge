"""The dimension budget that governs how shallow a level encoder can be.

Every gate is reversible, so at any point the eighteen register values are a
bijective image of ``(x, y, 0**6)``.  Their GF(2) span, together with the
constant, therefore has dimension at most 19, and it starts at 13: the constant
plus the twelve data bits.  So **six nonlinear dimensions** are available in
total, shared between the two sides.

At the kernel those six are exactly the six code bits, which leaves no room for
intermediates.  The span does not have to contain the raw data bits - the map is
a bijection whatever the registers hold - so an encoder may trade a data
dimension for a nonlinear one.  But every AND it still has to perform needs its
two operands inside the span, and the operands are functions of the data, so in
practice the data bits stay until the end.  An encoder that needs k nonlinear
intermediates at its peak therefore either borrows from the other side, which
forces the two encoders to run in series rather than in parallel, or uncomputes
them, and uncomputing is what inflates the AND count.

This module reports, for each encoder, the peak dimension its natural
quadrant-split network needs, which is the quantity that has to come down.
"""
import math

FULL = (1 << 64) - 1


def _rng(a, b):
    return set(range(a, b + 1))


NESTED = {
    'u1': [_rng(11, 27), _rng(12, 26), _rng(13, 25), _rng(15, 23), _rng(17, 21)],
    'v1': [_rng(32, 48), _rng(33, 47), _rng(34, 46), _rng(36, 44), _rng(38, 42)],
    'u2': [_rng(29, 53), _rng(35, 47), _rng(36, 46), _rng(37, 45), _rng(39, 43)],
    'v2': [_rng(2, 61), _rng(2, 26) | _rng(50, 60), _rng(2, 26) | _rng(51, 59),
           _rng(2, 26) | _rng(53, 57), _rng(2, 26)],
}


def level_classes(name):
    lvl = [sum(1 for s in NESTED[name] if t in s) for t in range(64)]
    cls = {}
    for t in range(64):
        cls.setdefault(lvl[t], []).append(t)
    return cls


def wires_needed(name, code_values=6):
    """How many wires a side must still occupy once its code is on three of them.

    The code has `code_values` distinct values; the junk wires have to separate
    the coordinates inside each code class, so 2**junk must cover the largest
    class.
    """
    cls = level_classes(name)
    biggest = max(len(v) for v in cls.values())
    junk = max(0, math.ceil(math.log2(biggest)))
    return 3 + junk, biggest, junk


def report():
    print('side  largest-class  junk-wires  wires-at-kernel')
    for name in ('u1', 'v1', 'u2', 'v2'):
        w, big, junk = wires_needed(name)
        print(f'{name:4s}  {big:13d}  {junk:10d}  {w:15d}')
    print()
    print('Total dimensions available: 19 (18 registers plus the constant).')
    print('At the kernel: 1 + 12 data + 6 code bits = 19, exactly full.')
    print('So every nonlinear intermediate must be uncomputed before the kernel.')


if __name__ == '__main__':
    report()
