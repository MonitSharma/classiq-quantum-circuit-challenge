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
