"""Conditionally clean wires available to each level encoder.

Khattar and Gidney (Quantum 9, 1752, 2025) formalise a resource between clean
and dirty ancillae: a wire whose value is *known* inside the branch that matters
can be treated as initialised there, and borrowed instead of allocated.

Here the branch that matters is "the code is nonzero".  Every code bit of an
encoder is zero off the support, so an affine form that is constant on the
support names a wire that is a known constant whenever the output is nonzero -
and is therefore usable as clean scratch for any product later ANDed with the
guard.  That is exactly the register pressure that blocks the AND-network
encoders, so this counts how much relief is available.

Result: one such wire for each disk-A encoder (bit 5, and two per quadrant under
the best split), and **none** for the pass-2 encoders, whose supports are 25 and
60 of the 64 coordinates.  The technique therefore relieves about half the
bottleneck.
"""
def R(a,b): return set(range(a,b+1))
NESTED={'u1':[R(11,27),R(12,26),R(13,25),R(15,23),R(17,21)],
        'v1':[R(32,48),R(33,47),R(34,46),R(36,44),R(38,42)],
        'u2':[R(29,53),R(35,47),R(36,46),R(37,45),R(39,43)],
        'v2':[R(2,61), R(2,26)|R(50,60), R(2,26)|R(51,59), R(2,26)|R(53,57), R(2,26)]}
def par(m,y): return bin(m&y).count('1')&1
for name,sets in NESTED.items():
    lvl=[sum(1 for s in sets if y in s) for y in range(64)]
    sup=[y for y in range(64) if lvl[y]>0]
    forms=[m for m in range(1,64) if len({par(m,y) for y in sup})==1]
    print(f"{name}: support size {len(sup)}; affine forms constant on it: {len(forms)} -> masks {forms}")
    # also: per quadrant of the two most useful bits, how big is the residual support?
    best=None
    for p in range(6):
        for q in range(p+1,6):
            worst=0
            for qp in range(4):
                c=[y for y in sup if (((y>>p)&1)<<1|((y>>q)&1))==qp]
                worst=max(worst,len(c))
            act=sum(1 for qp in range(4) if any((((y>>p)&1)<<1|((y>>q)&1))==qp for y in sup))
            if best is None or (act,worst)<best[0]: best=((act,worst),(p,q))
    print(f"    fewest active quadrants over all variable pairs: {best[0][0]} (split {best[1]}, largest cell {best[0][1]})")
