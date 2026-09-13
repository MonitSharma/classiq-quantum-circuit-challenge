# Where the 196 oracle's slack actually is, measured layer by layer

Protected best unchanged: **196 depth / 858 CX / 18 qubits**, `artifacts/196/`.
Nothing here is a new oracle. This file replaces estimates with measurements, and
every bound below is labelled with what it is conditional on.

## Stage accounting

`858 CX + 789 U3 = 2505` wire-slots; `18 * 196 = 3528` available; occupancy
**71.0%**. Per stage, with each encoder instance counted once:

| stage | depth | CX | U3 | wires | slots | occupancy |
|---|---:|---:|---:|---:|---:|---:|
| y encoder | 77 | 193 | 180 | 9 | 566 | 81.7% |
| x encoder | 77 | 191 | 181 | 9 | 563 | 81.3% |
| kernel | 43 | 89 | 69 | 8 | 247 | 71.8% |

The encoders run in parallel, so the oracle is `77 + 43 + 77 - 1`.

## The loader is source-bound, and the source load is nearly balanced

ASAP-layering the compiled y encoder gives, per layer: **56 layers with 3 CX, 11
with 2, 3 with 1, and 7 with none**. CX counts by control wire:

| wire | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CX as control | 56 | 3 | 48 | 3 | 56 | 3 | 8 | 8 | 8 |

Wires 0, 2, 4 are the low sources and carry 160 of the 193 CX; wires 1, 3, 5 and
the three outputs carry the 33 CX of the frame skeleton. A wire can control one
CX per layer, so **wire 0 alone forces at least 56 layers**, and the three low
sources together force at least `ceil(160/3) = 54`.

**A correction I had to make to my own first draft of this file.** I initially
divided the work evenly across the six hosts -- `(174 + 160 + 66)/6 = 67` -- and
concluded there were ten layers of slack per side. That averaging is invalid: a
host is blocked by *its own* operations, so the bound is the maximum over hosts,
not the mean. The binding host is one that needs all eight low masks in a frame:
it performs 8 rotations and a length-8 closed tour, so 16 operations, hence 16
layers for that frame. Four frames give 64, plus the 13 skeleton layers:

    4 * 16 + 13 = 77

which is exactly what the compiled loader achieves. `loader_floor` returns the
same 77 independently. **The loader has essentially no scheduling slack** -- the
seven CX-free layers and fourteen partly-filled ones are where the *other* hosts
idle while the binding host works, which no scheduler can remove. Splitting the
nine wires any other way is worse: four sources and five hosts gives a max-host
load that is larger still.

## Consequently

Within this staging the floor is `2 * 77 + 31 = 185` against 196 measured, and
**all 11 layers of reachable slack are in the kernel** (43 against its occupancy
bound of 31). **This is not an unconditional bound** -- it assumes the four-frame
skeleton, the current code and the current kernel representation -- but it does
say that closing every layer of reachable slack still lands at 185, well above
142. So 142 needs a different construction, not a better scheduler.

## The tightened bound retracts the earlier "balanced codes" result

The annealed label searches had reported codes with loader floors of 61-68 and
kernels of 139-146 terms, and I had recorded those as a real trade-off. Scoring
the same saved candidates with the **tightened** bound -- the one that includes
the per-wire contention term the audit's counterexample exposed -- every one of
them returns **77**, identical to the recorded codes, and the best point by
`2 * floor + 0.48 * T_K` is the recorded codes themselves at 197.2.

That retraction is consistent with what was measured at the time: those
candidates' loaders compiled to 70 and 72 against a predicted 68, and the
frontier candidates compiled to 225-233. The loose bound was flattering them.
So there is no cheaper-loader/dearer-kernel trade-off to exploit; the earlier
"flat frontier" reading was itself an artefact of the loose model.

## Degrees of freedom closed this round

| Attempt | Result | Nature |
|---|---|---|
| Affine relabelling of the loaded code bits, including mixing in the raw parity | all **10,752** maps per side give loader floor 77 and 90 kernel terms | **exhaustive** over the group |
| One code bit as a rank-2 quadratic (a single Toffoli), so the lookup drops to two outputs | no rank-2 quadratic splits either side's classes into groups of at most four | exhaustive over rank-2 quadratics |
| Cheapest class-splitting bit at all | minimum Walsh support **23** on the row side, **18** on the column side, over all `2^13` and `2^14` cell subsets | exhaustive over cell-constant splits |
| Wider CX layers in the beam (`fill` up to 4) | kernel 44, no better than 43 | bounded sweep |
| A*-style beam ranking, committed depth plus optimistic remainder (`horizon` 0 to 2.5) | kernel 43 at horizon 1.0, with more CX; no gain | bounded sweep |

The second and third rows matter because they close the cheapest route to a
two-output lookup: it needs one code bit that both splits the classes four/four
*and* is cheap to compute, and the cheapest splitting bit is not a quadratic.

## Still open

* A kernel schedule below 43 against its occupancy bound of 31 -- the only
  reachable slack left. Five algorithms and several thousand runs have not moved
  it; an anneal over integer lifts scored by *compiled depth* rather than by term
  count is running (`src/post196_lift_for_depth.py`).
* Avoiding the four-frame skeleton, or breaking the 16-layer binding host. Both
  need the code's Walsh terms to stop filling a whole low cube in some frame,
  which is a property of the code, not of the schedule -- and the annealed and
  exhaustive code searches above did not find one that keeps the kernel cheap.
