# In-place quotient-permutation screen

Updated September 11, 2026. This campaign tested whether the six x and six y
data bits could be permuted in place so that the 11-by-11 row/column quotient
became a cheap central phase. Unlike the earlier class-code experiments, this
hypothesis does not load a class label into ancillas.

## Exact quotient reconstruction

Grouping identical rows and columns of the exact 64-by-64 logo matrix gives
11 row classes and 11 column classes. Their populations are:

```text
rows:    22, 2, 2, 4, 4, 5, 12, 2, 2, 4, 5
columns: 4, 25, 7, 2, 2, 4, 4, 5, 2, 4, 5
```

The deterministic class extraction and quotient matrix are in
`artifacts/quotient_permutation_screen_200.json`. The reconstructed matrix
has exactly 1,097 marked points and its expansion is checked against the
original truth table before scoring.

## Free-layout screen

The first screen treated class permutations as free and assigned each class to
a contiguous binary address block. This is optimistic: it excludes the cost
of realizing the six-bit permutations and does not claim that contiguous
blocks are globally optimal. It sampled 200 independent row/column orderings
with seed `20260911`, scoring reduced OBDD nodes, a greedy exact dyadic cover,
and ANF literal cost.

The best sampled layout had:

| Proxy | Natural layout | Best free contiguous layout |
|---|---:|---:|
| Reduced OBDD nodes | 96 | 74 |
| Greedy dyadic rectangles | 97 | 61 |
| Greedy dyadic literal cost | 948 | 551 |
| ANF terms | 886 | 456 |
| ANF literal cost | 5,982 | 2,909 |

These are structural proxies, not native circuit depths. The selected dyadic
rectangles are disjoint and cover the transformed table exactly.

## Central native diagnostic and closure

To calibrate the optimistic proxies, the 61-rectangle exact cover was emitted
as a central phase diagnostic on the twelve data wires, with six additional
workspace wires available to the existing MCZ helper. The serialized
`u3`/`cx` diagnostic measured:

```text
depth 6456 / CX 5490 / width 18
```

This is far above the 150-depth optimistic cutoff. It shows that the cheap
quotient proxies do not translate to a cheap native phase: the rectangle count
and literal count conceal the cost of repeatedly synthesizing high-control
phase terms. No `P_x` or `P_y` reversible permutation search was started, and
no full conjugated oracle was generated.

The route is therefore closed under the tested central construction. This is
not a lower bound on every possible shared implementation of the quotient;
reopening it would require a new central phase primitive that materially
beats the 6,456-depth exact diagnostic before spending time on data-register
permutation synthesis.
