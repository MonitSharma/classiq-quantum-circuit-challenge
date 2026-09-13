# Where the depth goes in the 196 oracle

**Corrections applied.** An earlier version of this file overstated its results
in four ways, each found by the audit in
[`POST196_FLOOR_AUDIT.md`](POST196_FLOOR_AUDIT.md) and reproduced here before
being fixed:

1. the frame cost function was called *exact*; it is a lower bound, and
   `src/post196_frame_model_audit.py` exhibits a case where it returns 4 against
   a true 13. It has since been tightened (see below) but is still a bound;
2. the claimed general kernel floor `3 * T / 8` is **false** -- eight independent
   singleton parities are eight parallel Rz gates at depth 1, while the formula
   returns 3. The valid occupancy bound for a fixed representation with `T`
   parities on `n` wires is `ceil((T + 2 * max(0, T - n)) / n)`, which is **24**
   at `T = 69, n = 8`, not 26;
3. the occupancy figures were wrong: the serialized QASM has 858 CX and 789 U3,
   so 2,505 wire-slots, **71.0%** occupancy of `18 * 196`, and an occupancy
   bound of **140** -- not 65% and 139;
4. annealing was described as establishing a global optimum over labels and over
   `GL(6,2)`. It does not. `GL(6,2)` has 20,158,709,760 elements and nothing here
   enumerated it.

What survives is stated as such below.

**Latest audit:** The new frame model is not an exact joint scheduler, and annealing does not prove a GL(6,2) or code optimum. See [ARITHMETIC_MIDDLE_PROBE.md](ARITHMETIC_MIDDLE_PROBE.md) for a concrete contention counterexample and measured arithmetic components.

**Audit correction:** The universal 150-depth exclusion and packing figures below are not established. See [POST196_FLOOR_AUDIT.md](POST196_FLOOR_AUDIT.md) for a real omitted 94-term code, the nonexhaustive search, invalid kernel bound, and corrected occupancy. The text below is retained as the historical analysis, not an accepted proof.

September 13, 2026. Written after the leaderboard moved to **142** and the
target became sub-100. The verified local best is **196 / 858 / 18**
(`artifacts/196/`). This document is the answer to "can the current
architecture get there", and the answer is no, with numbers.

## The 196 circuit, by stage

| Stage | Depth | What it is |
|---|---:|---|
| loaders (in parallel) | 77 | three-bit class code per side, six address bits |
| kernel | 43 | eight-wire diagonal phase polynomial, 69 parity terms |
| inverse loaders | 77 | exact inverse of the loaders |
| total | **196** | one layer of cross-boundary merging |

The loader is 79% of the cost, so every bound below is about the loader.

## Two independent floors for the loader

The loader is a nine-wire phase polynomial, Rx- or H-conjugated on the three
outputs, in which **every parity contains exactly one output variable**. That
one structural fact drives everything:

* a wire can host a rotation only if its value carries exactly one output
  variable, so wires holding pure control parities -- the ones that supply the
  CX deltas -- cannot host rotations;
* with `s` pure sources and `9 - s` hosts, each host performs
  `2 * T_L / (9 - s)` operations, and each source can be the control of only
  one CX per layer, so the sources alone need `(T_L - (9 - s)) / s` layers.

`s = 3` minimises the larger of the two. With the current codes
(`T_L = 174` and `175` Walsh terms) that is `max(58, 56) = 58` layers plus
about 13 layers of frame skeleton, so **about 71**. Measured: **77**, over 260
`post224_relative_lookup` seeds and 130 seeds of `post218_bank_loader`, which
schedules each frame with exact shortest closed Hamming tours, staggered
cyclic bit orders, and conflict-aware interleaving. The residual 6 layers are
scheduling slack, not architecture.

## The loader/kernel trade-off is flat

Sparser codes make the loader cheaper and the kernel dearer. This was measured
end to end in a single harness (`src/post196_code_frontier.py` for the codes,
then compiled):

| codes | loader terms | kernel terms | loaders | kernel | oracle |
|---|---:|---:|---:|---:|---:|
| `artifacts/218` | 175 | 89 | 77, 77 | 58 | 211 |
| frontier #1 | 105 | 153 | 67, 70 | 93 | 230 |
| frontier #2 | 99 | 161 | 66, 68 | 101 | 233 |
| frontier #3 | 99 | 162 | 66, 66 | 94 | 225 |
| frontier #4 | 104 | 156 | 68, 67 | 92 | 227 |

(This harness uses the plain low-degree ANF for every candidate, so the
reference row is 211 rather than 196; the recorded integer lift takes the
`artifacts/218` kernel from 89 terms to 69 and from 58 layers to 43. The
comparison between rows is what matters.)

The code search is not annealing. A four-bit-per-side code is one raw parity
plus a three-bit label per (raw parity, class) cell, so the three loaded bits
are indicators of three cell subsets and the only requirement is a 36-element
set-cover: within each raw fiber the triple must separate the cells. Enumerate
two subsets over the spectrally sparsest pool and the third is forced up to the
orientation of each connected component of the "must separate" graph, so it
can be solved exactly rather than searched.

## The floor, and why sub-100 is out of reach here

Exact minimum Walsh support of a **single** cell-constant bit that separates
anything at all: **23** on the row side (rho = 32), 4 on the column side. All
three bits must vary, so `T_L >= 69` on the row side as a hard bound; the best
separating triple actually found is 97.

Substituting the best case into the two loader floors and the kernel's own
wire-slot floor (`3 * T_K / 8`):

| point | loader floor (each) | kernel floor | oracle floor |
|---|---:|---:|---:|
| (174, 69) | 71 | 26 | 168 |
| (97, 166) | 45 | 62 | 152 |
| (105, 153) | 48 | 57 | 153 |

So the *practical* floor is near 178 across the whole frontier, and the
unconditional one is near 125. Sub-100 is excluded either way by the code's
spectral sparsity: the sparsest separating triple found is 97 Walsh terms, and a
single useful row-side bit needs at least 23, so `T_L >= 69` is a hard bound and
`2 * (T_L - 3) / 3` alone is already 44 before any kernel.

## Alternatives measured, and why each fails

| Route | Measurement | Why it fails |
|---|---|---|
| Direct phase polynomial, no ancillas | Walsh support of the logo is **4096 of 4096**; ANF 886 monomials, degree 12, downward closure 4096 | ~680 layers; the predicate has no sparse phase representation |
| Wider codes (3 raw parities + 2 loaded) | loader terms drop to 97 and 90, but reachable kernel inputs rise to **837 of 1024**, ANF degree 8, **711** kernel terms, **382** layers | raw parity bits destroy the don't-care compression the kernel lives on |
| Low-degree loaded bits (compute with Toffolis, not a lookup) | space of class-constant functions of degree <= 3 is **constants only**, both sides; degree 4 gives 8 of 11 row signatures; row codes need degree 6, column codes degree 5 | no cheap ANF; monomial-by-monomial loading is far worse than the lookup |
| Two-frame loader (each bit ignoring one transformed coordinate, which would nearly halve the loader) | SAT over 250 sampled independent direction triples per raw parity, **all UNSAT** | sampled, not exhaustive, but no witness exists in the sample |
| XAG / multiplicative-depth route | exact XAG is 81 ANDs at MD 6, but the six-ancilla pebbling needs **304** nonlinear toggles; the lowered circuits in `artifacts/multiplicative_depth/` are **1023-1046** depth | live width 11 exceeds the six clean ancillas, so recomputation dominates |
| Boolean loading of an interval indicator | `[13,25]` needs four maximal subcubes of codimension 6, 5, 3, 5, i.e. about 58 CX and 50 layers for one of the six nested sets | a lookup that produces all 192 table entries in 77 layers is far more efficient than evaluating the bits explicitly |
| Coordinate symmetry to shrink the lookup address | best XOR `v` leaves 20 of 64 rows mismatched; the predicate's best is 90 of 4096; class sizes 5 are odd so no reversible map can shrink the address below six bits | no five-bit quotient exists |

## Correction: 142 is *not* excluded by these bounds

An earlier version of this document claimed 142 was below the architecture's
floor. That was wrong: it added the frame skeleton into what was presented as an
unconditional bound. The unconditional part is only this. Every rotation after a
host's first needs one CX whose *control* is a source wire, so with `S` sources a
schedule needs at least `(T_L - H) / S` layers, and the busiest of `H` hosts
performs at least `(2 T_L - H) / H` operations; at `S = 3, H = 6` the binding one
is `(T_L - 3) / 3`. With the kernel's own `3 * T_K / 8`, the unconditional floor
is

`2 * (T_L - 3) / 3  +  3 * T_K / 8`

which is **140** at (174, 69) and **125** at (97, 166). So 142 is inside what the
architecture could in principle do, and the gap to 196 is scheduling quality,
not structure.

What the skeleton adds is conditional but seems unavoidable in practice. Hosts
are three contaminated control wires, so the high coordinate bits are not
available as sources and have to be uncopied, shifted and recopied at every
frame boundary: about 13 layers. A skeleton-free schedule would need each loaded
bit's spectrum to live inside `{h_i} union low`, i.e. to be independent of two of
the six coordinates, which is strictly stronger than the two-frame condition that
was already SAT-unsatisfiable on every sampled triple. Adding that skeleton gives
a *practical* floor of `2 * (T_L / 3 + 13) + 0.53 * T_K`, which is 179 at
(174, 69), 178 at (97, 166) and 178 at (105, 153) -- remarkably flat, and about
17 layers below the current 196.

## What a faster architecture has to look like

Counting gate-wire occupancy is the clearest hint. The 196 circuit has 858 CX
and 789 u3, so it occupies `2 * 858 + 789 = 2505` wire-slots. At width 18
and depth 196 there are 3528 slots available, so it runs at **71.0% occupancy**,
and the shortfall is entirely structural:

| window | layers | wires busy | occupancy |
|---|---:|---:|---:|
| loaders | 77 | 18 of 18 | 76% |
| kernel | 43 | 8 of 18 | 27% |
| inverse loaders | 77 | 18 of 18 | 76% |

A perfectly packed circuit with the same 2505 slots would be depth **140**. That
is a bound, not a schedule: dependencies and incompatible wire usage can prevent
packing, and its proximity to the leader's 142 does not reveal anything about
the leader's method -- reducing the gate count would lower depth just as well.
The kernel window is the
waste: ten wires hold coordinate data and cannot host a kernel parity, because
a kernel parity is a parity of code bits and those wires carry `x_i` or `y_i`.

So the target is an oracle in which **no wire is idle**: the phase work has to
be spread over all eighteen wires instead of being concentrated in an
eight-wire kernel between two loaders. Pipelining the existing stages does not
achieve that -- splitting the loader so the kernel can overlap costs more than
the kernel saves, because a two-output loader is not much cheaper than a
three-output one (the terms, not the outputs, set the cost).

## Loader lower bound, and what the searches do and do not show

The estimates above used a linear fit. `src/post196_frame_balance.py` replaces it
with a lower bound on the loader's frame cost. In frame `f` each of the six hosts must visit
a subset of the three low-bit masks; that subset costs `TOUR[subset]` CX gates
(minimum closed Hamming tour from 0, precomputed by Held-Karp over all 256
subsets) and `popcount(subset)` rotations, the host is busy for the sum, and the
three low wires supply at most three CX gates per layer. A closed tour from 0 that visits any mask with bit `k` set must toggle bit `k` an
even and nonzero number of times, so it occupies low wire `k` at least twice. So

    frame bound = max( max_host(rotations + tour),
                       ceil(total_tour / 3),
                       max_k sum_hosts 2 * [host subset touches bit k] )

summed over four frames plus thirteen layers of frame skeleton, minimised over
all 120 high-wire choices and output pairings.

The third term was added after the audit: without it the function returns 4 on
six hosts that each need low masks {0, 1}, where low wire 0 alone requires twelve
CX and an explicit schedule takes 13 layers. With it that case returns 12. This
is still only a bound -- the joint scheduling problem is not solved -- so it can
be loose on tables it has not been checked against.

**Calibrated at one point, loose elsewhere.** On the recorded 218 codes it
returns 77 for both sides, which is what the compiled loaders achieve; a bound
that is attained is an optimum *for those codes within this frame design*. On an
annealed alternative it returns 68 against 70 and 72 measured, which is the gap
being described.

Two searches then probe the space. Neither is exhaustive and neither certifies
an optimum:

* **Codes.** Annealing the cell labelling against `2 * loader_floor + 0.48 * T_K`
  (the 0.48 calibrated so the 218 codes predict 197 against 196 measured), from
  the 218 labelling, four seeds and both viable x raw parities: every run with
  `rho = 48` returns to the 218 codes at 197.2, and every `rho = 16` run lands at
  205-211 -- a cheaper loader bound of 66-72 bought with a kernel of 139-146
  terms. So no annealed label set beat the 218 codes; that is a negative search
  result, not optimality. The frontier search in `post196_code_frontier.py` was
  separately found to have a bug (`complete()` returned free cells the caller
  never varied), now fixed as `completion_subsets()`; with the fix one row-side
  pair reaches 94 terms where the buggy version reported 97.
* **Wire basis.** `src/post196_frame_basis.py` anneals over invertible CNOT
  re-basings of the six coordinate wires, which relabel every Walsh mask and so
  move terms between frames while leaving the code values, the class cells, the
  kernel table and the kernel lift completely unchanged -- the only price is the
  CNOT depth, paid twice. One basis vector is pinned to the raw parity so the
  kernel still finds it. Over six restarts per side the best result is the
  identity, over fourteen annealed restarts per side with the tightened bound.
  Because the function is a valid lower bound and is *attained* at the identity,
  every sampled basis is at least as expensive as the 77 actually achieved --
  but the sampling covers a vanishing fraction of `GL(6,2)`, so this is evidence,
  not a proof.

So: several independent searches all return to 196, and every alternative that
was actually compiled measured worse. That is the honest summary. It is not a
proof that the architecture cannot do better, and the corrected bounds above no
longer exclude 142.

## What would have to change

The binding terms are the factor two for compute/uncompute and the roughly
sixty-four rotations per loaded bit. A sub-100 construction has to break one of
them, which means one of:

1. a feature set that is *both* cheap to compute and gives a sparse kernel --
   the measured trade-off says the class codes are not it;
2. a loader that is not rotation-per-table-entry, i.e. a Boolean circuit whose
   cost is not bounded below by the code's Walsh support. The degree analysis
   above says the codes are degree 5-6, but degree is not circuit cost, so the
   open question is the **multiplicative complexity of a separating code**,
   which has not been computed;
3. an oracle that is not of the form `E^dagger K E` at all.

Item 2 is the concrete open question and the cheapest to settle next: find, for
the row and column sides, the minimum AND-count reversible circuit that maps
`|y,000>` to `|y,c(y)>` for *some* class-determining code, with the three clean
ancillas as the only workspace. If that is materially below 30 ANDs per side
the architecture becomes viable again; if not, item 3 is the only route left.

No cloud resynthesis or challenge submission was performed, and no background
optimiser or leaderboard monitor is left running.
