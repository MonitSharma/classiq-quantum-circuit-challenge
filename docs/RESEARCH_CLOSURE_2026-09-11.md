# Research closure: classical logic compression to reversible depth

Updated September 11, 2026. This note consolidates the latest closure rather
than claiming that the challenge is impossible.

The protected exact fallback remains depth 524 / CX 950. The target leaderboard
gap is therefore 524 to an observed 183-depth entry. The completed campaigns
now provide substantial evidence against the broad strategy of first finding
an efficient conventional Boolean representation and then reversibilizing it
with compute/phase/uncompute:

| Representation | Strongest relevant evidence | Disposition |
|---|---|---|
| XAG / low multiplicative depth | 81-97 AND classical networks, but native realizations around 1023/899 or worse; destructive dirty-span screens found no phase frontier | Closed |
| BDD / ESOP / Walsh / phase polynomial | Classical simplification or full phase expansions did not produce a competitive native network | Closed |
| LUT single-target | Corrected 3-, 4-, and 5-LUT forward estimates of 462/249, 965/539, and 2297/1334 depth/CX | Closed |
| Quotient/class layouts | 11-by-11 quotient structure; corrected exact 61-rectangle central phase compiled to 5877/4682 and was exhaustively verified | Closed |
| Feature loaders, row/column codes, phase histories, MPO/QBP/ZH probes | Exact prototypes were far above target or failed to expose a compact unitary representation | Closed as tested |

The corrected LUT result is especially important. The 462-depth 3-LUT path is
still optimistic: it excludes the 18-wire reversible schedule, dirty-target
conflicts, garbage/rematerialization, the central phase, and the inverse. A
naive `C† P C` interpretation is already about `2*462+1 = 925` depth before
those costs. The earlier 145/86 estimate was invalid because truth-table bits
had been mistaken for ANF coefficients; it is explicitly deprecated.

The appropriate conclusion is:

> Classical logic compression is not translating into native quantum depth for
> this instance under the tested representations.

This is not a lower bound on every hand-designed single-target network and does
not rule out a qualitatively different operator-level construction. It does
mean that another incremental Boolean representation, another generic
compute/phase/uncompute compiler, or another larger reversible pebbling beam is
not a sensible competition bet without a new external architectural clue.

The remaining high-ROI work is narrower: reverse-engineer a likely winning
architecture from leaderboard metrics and challenge constraints, or identify
an operator-level construction with a credible native-depth estimate before
implementing it. No rank-one result or submission is claimed.

## Shared-address descriptor screen

The proposed shared-address QROM route was screened mathematically in
`src/shared_address_descriptor.py`.  Exact row/column quotienting gives 11
classes on each side, hence a minimum 4+4-bit binary descriptor.  Optimizing
2000 random class-label assignments produced a best middle kernel with 86 ANF
terms, 366 literals, degree 8, and dense 8-bit Walsh support (256/256).
This is not an impossibility proof for a genuinely phase-tolerant shared
traversal, but it falsifies the unsupported inference that compact addresses
automatically yield a <=55-depth kernel.  No QROM circuit was generated.

The final co-designed monomial embedding probe searched whole six-wire
X/CX/RCCX semantic permutations, allowing arbitrary placement of the four
required y-code bits and two garbage wires. A 1500-state beam through 16
primitives found no exact boundary map; its best exact distinct-wire score was
186/256 exact score in a completed four-primitive beam, with no exact map. This closes the tested monomial embedding family, not every
reversible or phase-tolerant QROM construction. No x-side or full oracle was
started because the exact y embedding never reached the <=70-depth gate.

The implementation was then audited: the prior 555/358 y-loader had targeted
all three `m` bits onto q13 and was invalid. The corrected four-output probe is
555/359, so the old native measurement is retracted. A bucket multiplicity
proof also shows that four code bits plus two garbage bits cannot be a
reversible six-wire embedding (largest buckets 25 and 20). A new affine
3+3-ancilla screen found rank-5 linear garbage projections injective within all
code buckets on both sides. This is a positive resource result, not yet a
native circuit; it is the only remaining comparator experiment worth a bounded
lowering attempt.

That bounded 3+3 lowering was completed for both admissible y kernel
directions and all overwrite choices. The best exact native y encoder was
1491/845 depth/CX, with complete 64-input mapping and inverse-restoration
checks. It fails the <=70-depth criterion, so the tested comparator family is
closed; this remains an empirical closure, not a proof against every
phase-tolerant QROM construction.
