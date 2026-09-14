# Protected-label encoder analysis (step 1 of the audit's plan)

## Segmentation of the protected 190

Found by taking the longest gate window whose union of coordinate wires is <= 2
(`src/post190_segment_protected.py`). The phase stage sits on coordinate wires
4 and 11 -- the two exposed raw features -- plus the six ancillas.

| stage | gates | depth | CX |
|---|---|---|---|
| encoder | 754 | **83** | 389 |
| phase | 137 | **35** | 80 |
| uncompute | 750 | **79** | 388 |
| whole | 1641 | 190 | 857 |

Standalone depths sum to 197; the packaged circuit measures 190, so the stages
overlap by 7 layers when scheduled together.

**The phase stage already meets the audit's <=35 budget.** Against the
50/35/50 = 135 target, the entire remaining saving must come from the encoder
(83 -> 50) and its inverse.

Scratch available during the encoder: only wires 4 and 11 must hold correct
values when the phase begins, so the other **ten coordinate wires are free
scratch** (the inverse restores them). Register pressure is much weaker than
the earlier notes assumed.

## Exact shared-XAG synthesis

`src/post190_exact_xag.py` is a CNF (pysat/Cadical) exact-synthesis encoder:
six inputs, k AND nodes, each AND input an XOR of earlier signals plus an
optional constant, outputs arbitrary XORs. XOR and NOT are free; AND nodes are
the cost.

Controls: MAJ3 is UNSAT at k=0 and SAT at k=1, recovering the known optimum
`MAJ3 = a XOR (a XOR b)(a XOR c)`.

Result on the protected labels (3 fixed outputs per side):

| side | k=3 | k=4 |
|---|---|---|
| y | **UNSAT** (1.7s) | unresolved |
| x | **UNSAT** (0.9s) | unresolved |

So a shared encoder for the protected labels needs **at least four AND nodes per
side**. That is a proven lower bound, not a search failure. k=4 is open.

A z3 bitvector encoding of the same problem timed out at k=4 after 90s; the CNF
encoding proves k=3 UNSAT in under two seconds, so it is the right tool.

## Routes measured and found uncompetitive

* ANF-monomial accumulation needs a prefix closure of **47 products (y)** and
  **50 (x)**, i.e. roughly that many AND nodes per side -- worse than the
  current encoder.
* Nechiporuk-style half-split would need all 8+8 minterms live per side, which
  does not fit the available scratch.

## Not established

No encoder below 83 layers has been produced. k>=4 per side is open in both
directions. Nothing here shows the protected labels are the right ones to keep;
step 2 of the audit's plan (relabel, charging the full kernel cost) is untouched.

## Update: witness search, and a cheaper target found on the way

Tooling extended (`src/post190_exact_xag.py`): witness extraction (decoded and
checked against the known `MAJ3 = a XOR (a XOR b)(a XOR c)` optimum) and an
optional `chain=True` restriction (gate j may use the inputs plus only gate j-1).

Searches run and their outcomes:

| instance | result |
|---|---|
| y, x 3-output, k=3 | **UNSAT** (~1s each) -- proven bound |
| y 3-output, k=4 | unresolved (>200s) |
| y 3-output, k=10 descending | unresolved (>200s) |
| y 3-output chain, k=6 | unresolved (>100s) |
| y0 single output, k=3 | unresolved (>170s) |

A commutativity symmetry-breaking clause was tried and **reverted**: it made even
the MAJ3 control hang, so it was wrong. Correct symmetry breaking remains the
obvious unlock and is not yet in place.

### The binding constraint on any witness

An AND gate must write its output into a wire holding **zero**. Only the six
ancillas are zero, three per side, and those three must end holding the code
bits. Coordinate wires hold live input data. So any k-gate XAG needs a
three-pebble schedule per side, with recomputation if k exceeds what three
pebbles hold. A "flat" XAG (all AND inputs linear in the primary inputs) would
need only one pebble but can only express degree-2 functions, and these code
bits have degree 5-6. So depth is forced, and depth costs pebbles.

### A cheaper target noticed while measuring

The encoder performs 384 rotations (6 code bits x 64) with 389 CX in **83
layers**, i.e. 4.63 rotations per layer. For this particular circuit each
rotation is paired with its own CX, so the occupancy argument does apply here:
with `2c + r <= 18` the throughput ceiling is 6/layer, giving `384/6 = 64`
layers. **The existing multiplexer encoder has roughly 19 layers of scheduling
slack against its own representation**, independent of any Boolean rewrite.

That is a smaller prize than a Boolean encoder but far more likely to land, and
it is measured against the protected package rather than inferred.

## The scheduling route is closed (measured)

Layer-by-layer occupancy of the protected encoder
(`src/post190_encoder_occupancy.py`):

* depth 83, 389 CX, 365 u3, mean wire occupancy 77%
* the dominant layer profiles are `cx=6,u3=6` (15 layers) and `cx=6,u3=5` (18) --
  `2*6+6 = 18` wires, i.e. **the busy layers are already at the ceiling**
* **17 layers carry zero rotations**; 10 carry zero CX

Those 17 pure-CX layers are the basis transitions, and they are *not* recoverable
slack. During a transition every host is occupied by CX; the only free wires are
the three sources, which hold bare address bits, while every needed parity
contains an output bit. So nothing can rotate during a transition.

With three sources each host reaches only `2^3 = 8` parities per basis, and
`6 hosts x 8 = 48` per basis, so covering 192 requires **four bases and three
transitions**. Wanting 3 rotations/layer forces 3 CX + 3 Rz, hence 6 hosts and 3
sources on 9 wires -- the structure already in use. The transitions are therefore
structural, not a scheduling artefact:

    78 per side = 64 (rotations at the ceiling) + ~14 (transitions + prologue)

A parameter search over 12 seeds x 21 high-splits x 3 walk modes
(`src/post190_sweep_param_search.py`) returns **depth 78 for every single
combination** on both sides; only the CX count varies (194-204). The composed
encoder measures 83.

**Correction to the previous note in this file:** the claim of "roughly 19 layers
of scheduling slack" was wrong. The busy layers were already saturated and the
17 pure-CX layers are irreducible in this multiplexer family. The protected 190
sits essentially at this architecture's floor, and no scheduling saving is
available.

This leaves the Boolean encoder as the only route with upside: a k=4-6 XAG per
side, if it exists and can be scheduled with three pebbles, would plausibly fit
the 50-layer encoder budget (a Toffoli is ~6 layers).
