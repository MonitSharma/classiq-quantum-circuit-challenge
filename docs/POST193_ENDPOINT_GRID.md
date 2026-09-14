# 193 -> 190 by widening the endpoint search's configuration grid

Verified best is now **190 depth / 857 CX / 18 qubits**, `artifacts/190/`, SHA
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`. All 4,096
basis inputs pass with one shared global phase, maximum error 7.78e-15, zero
ancilla error; five dense random states pass at 2.16e-16; and
`src/build_permuted_oracle_package.py` replays the package to the same SHA.
The 193/853, 192/862 and 191/855 packages are preserved.

## Where the depth actually is

Profiling the 193 circuit first, rather than guessing:

* the two loaders finish between layers 73 and 77, and the eight kernel wires
  arrive at 75-77 -- essentially all at the loader depth;
* the kernel spans 38-40 layers on each of its wires;
* predicted depth `max_w (forward[w] + kernel span + inverse[mapping[w]])` is
  exactly 193, so the oracle is `77 + ~39 + 77` with one layer of merging;
* the busiest wire carries 181 gate slots, so the per-wire floor is 181 and was
  *not* the binding constraint.

Two consequences. The loaders are not reducible here -- every ancilla arrives at
the loader depth, and 77 is that construction's floor. And the asymmetric
forward/inverse loader search, rerun against the shipped kernel over 16,113
gauge-compatible pairs, predicts a minimum composed depth of exactly 193: it
cannot help while the kernel span is 39. **Only the kernel span was reducible.**

## What produced the gain

`post193_endpoint_beam` cycled sixteen `(alpha, timew)` pairs at one beam size.
Two beam options existed but had never been combined with the relaxed endpoint
contract: `horizon`, which ranks beam states by committed depth plus an
optimistic remainder instead of by fewest parities left, and `fill`, which allows
wider CX layers. Adding both to the grid, and recomputing arrival times from the
loaders the package actually ships (298/506, not the 99/155 the earlier sweep
used), gave the sequence:

| sweep | grid | result | depth histogram |
|---|---|---|---|
| v2 | original 16 pairs, shipped arrivals | 193 | 193:1 194:3 195:10 196:20 197:27 |
| v3 | + `horizon`, `fill`, beams 64-128 | **192** | 192:1 193:4 194:13 195:28 196:46 |
| v4 | focused: horizon on, timew 0.7-1.2 | **191** | 191:1 192:7 193:18 194:28 195:36 |
| v5 | extended: timew 1.0-1.8, horizon 1.5-2.2 | **190** | 190:1 191:4 192:17 193:48 194:56 |
| v6 | pushed: beam 192, branch 28, horizon 4.5 | no gain in 128 seeds | 191:3 192:4 193:15 194:24 |
| v7 | back to the v5 region, sampled harder | **190 / 857** | 190:2 191:3 192:23 193:48 194:72 |

Every winning configuration sat on the previous grid's boundary, which is why
the grid was pushed three times; v6 is the first push that did not pay, so the
useful region appears to be beams 96-128, branch 18-22, alpha 5-7, timew 1.0-1.4,
horizon 1.5-2.2, fill 2-3.

The first 190 (859 CX) came from seed 123, beam 128, branch 22, alpha 6.0,
timew 1.0, horizon 2.2, fill 3; the shipped 190 / 857 from seed 56, beam 96,
branch 22, alpha 6.0, timew 1.4, horizon 1.5, fill 2. In both the kernel's output
ancilla permutation is absorbed by rewiring the inverse loader, so it costs no
gates.

## The loaders are still at their own floor

Checked again for the codes this package actually uses, rather than assumed: both
sides have Walsh support 174 and 175, the frame-cost bound returns **77**, and the
compiled loaders are **77**. So the `77 + span + 77` arithmetic holds, 190
corresponds to a span of about 36, and the kernel's gate-occupancy bound is near
29 -- the span is the only term with room left in it.

## Scope

These are bounded searches, not bounds. Depth 190 is 4 above the observed
`77 + span + 77` arithmetic at span 36, and the kernel's own gate-occupancy
bound is near 29, so the kernel span is not yet exhausted. Nothing here changes
the address-width closure in `ADDRESS_WIDTH_CLOSURE.md`: the loaders remain at 77
and sub-140 still needs a different descriptor, not a better schedule.
