# Dual-register classifier/comparator experiment

## Result

The proposed structural identity is exact for one explicit labeling:

```text
f(x,y) = (b == c) AND (lvl <= m)
         XOR ((NOT b) AND c AND (m >= 6))
```

The 64-entry x and y tables, including locally interchangeable labels under
the fixed opposite register, are stored in
`artifacts/comparator_oracle/structure.json`.  The reproducible audit is
`src/comparator_oracle_structure.py`; it compares directly against
`src/search.py::logo` over all 4096 inputs and reports **0 mismatches**.

This validates the classical identity only.  It does not establish a cheap
reversible implementation.

## Physical register conclusion

The representation contains eight logical code bits:

| quantity | logical width | plausible location |
|---|---:|---|
| `c`, `lvl[0:3]` | 4 | destructively in q0..q5, with reversible garbage retained |
| `b`, `m[0:3]` | 4 | destructively in q6..q11, with reversible garbage retained |
| comparator scratch | up to 6 | q12..q17 |

Using all six clean ancillas as code outputs would leave no clean kernel
workspace.  Therefore the claimed one-/two-ancilla classifier counts require
destructive data-wire use or a more complicated dirty-wire schedule; they are
not established by the code tables alone.

## Native y-loader probe

`src/comparator_oracle_loader_probe.py` constructs the exact four y output
bits using the existing relative-phase MCX/ESOP machinery, with q0..q3 as
temporary dirty wires.  It is transpiled with
`qubits_initially_zero=False` to the required `u3`/`cx` basis.

| artifact | depth | CX | width |
|---|---:|---:|---:|
| `artifacts/comparator_oracle/y_loader/y_loader_esop_probe.qasm` | **555** | **359** | 18 |

The original 555/358 entry was invalid because all three m bits were targeted
onto q13. The corrected result is 555/359 on the clean-x slice, but fails the
4096-input reusable-loader check with **3696 mismatches** because its MCX
scratch is not dirty-safe.
This fails both the semantic and primary native-loader criteria. It is an
invalid loader-only diagnostic and is not promoted.

## Decision

The exact identity is a useful classical description, but the first concrete
native lowering is decisively noncompetitive.  The x-loader, parallel-loader,
kernel, and full `L† K L` synthesis were not attempted because this lowering
already fails the hard criterion by nearly an order of magnitude.  The result
does not prove that every possible hand-designed classifier is impossible; it
closes this ESOP/relative-phase-MCX lowering.

The protected 524/950 artifact under `artifacts/524/` was not modified.

## Co-designed in-place monomial embedding

The remaining variant searched the complete six-wire semantic state under
X/CX/RCCX transformations. Four output wires were selected jointly from all
`6P4` placements; the two remaining wires were unrestricted garbage. A
width-500 beam was completed through four primitives. The best fast-bound
score was 192/256 and the best exact distinct-wire score was 186/256; no exact
`(b,m)` boundary map was found. Longer runs were stopped for throughput. The report is
`artifacts/comparator_oracle/y_loader/whole_register_search.json`.

This closes the tested co-designed monomial embedding search, but not every
possible reversible embedding or phase-tolerant QROM traversal. Since no
exact candidate was found, there is no native loader depth to promote and the
<=70-depth GO condition was not met.

## 3+3-ancilla affine-isometry screen

The fixed-label bucket multiplicities make the original six-wire embedding
impossible: the largest x bucket has 25 inputs and the largest y bucket has
20, while four code bits leave only two garbage bits. A reversible embedding
therefore needs five garbage bits per side. The exact resource identity is
`6 data + 3 clean ancillas = 9 wires` on each side.

`src/comparator_isometry_affine_screen.py` searched affine garbage projections
and found rank-5 projections injective within every code bucket on both sides:

| side | classes | max bucket | affine masks |
|---|---:|---:|---|
| x | 11 | 25 | 52, 39, 24, 1, 29 |
| y | 12 | 20 | 22, 52, 45, 35, 32 |

The report is `artifacts/comparator_oracle/three_plus_three_affine_screen.json`.
This is a genuine positive resource result, but not yet a native classifier:
the three nonlinear code outputs and one fourth code output still need a
physical reversible construction. The next valid experiment is therefore a
3+3 affine-isometry lowering, not another six-wire permutation beam.

## Shared-address descriptor screen

The follow-up hypothesis was tested mathematically before circuit generation
by quotienting the exact 64x64 predicate into identical row and column
patterns.  The screen is implemented in
`src/shared_address_descriptor.py` and its complete report is
`artifacts/shared_address_descriptor/descriptor_report.json`.

There are exactly 11 row classes and 11 column classes, requiring at least
four binary descriptor bits on each side. The original screen was incomplete:
it only used labels 0..10 and forced all 135 unreachable addresses to zero.
The reopened screen allows arbitrary distinct 4-bit labels and records a
reachable-domain completion witness with **31 ANF terms, 154 literals,
degree 7** (35 marked reachable descriptor pairs; three unreachable addresses
are flipped). This is still a mathematical screen only; no QROM circuit was
claimed.

This does not prove that every shared-address QROM construction is
impossible, because a phase-tolerant traversal could exploit structure not
captured by an 8-bit ANF.  It does show that “compact descriptor” does not by
itself imply a <=55-depth kernel.  A future revisit would require an explicit
shared traversal primitive with native depth accounting, not another binary
label permutation or codeword-conditioned phase expansion.

## Whole-register semantic probe

The serialized probe was profiled in
`artifacts/comparator_oracle/y_loader/esop_failure_profile.json`. It has 162
pre-lowering RCCX operations; after lowering, q0 is the most heavily used
wire (289 operations and 162 CX participations). This confirms that the 555
depth is primarily a dirty-scratch/target serialization problem, not merely a
large number of independent gates.

`src/whole_register_y_search.py` then searched complete six-wire truth
signatures under X/CX/RCCX, scoring only four designated boundary outputs and
leaving two wires as unrestricted garbage. After correcting the input
signatures and tracking exact distinct-wire assignments separately, a
completed four-primitive beam reached 186/256 exact score (relaxed upper bound
192/256), with no exact boundary map. Longer arbitrary-placement runs were
stopped for throughput and are not treated as negative evidence. The search is
therefore a bounded diagnostic, not a proof against all reversible embeddings.

Nevertheless, the only completed native classifier probe is 555 depth and
invalid on arbitrary x, far beyond
the requested 70-depth kill threshold.  Per the experiment protocol, the
comparator architecture is **closed for this lowering**; x-side synthesis and
kernel integration were not started.

## 3+3 native lowering result

`src/three_plus_three_native.py` implements the proposed construction for both
y kernel directions (`28` and `35`) and all four choices of the overwritten
code bit. The k=35 run uses a genuinely different kernel-orthogonal affine
basis, with collision detection and a raw 64-input mapping check in the
generator. It computes three code bits into clean outputs and realizes the
fourth with a degree-3 care-set correction.

The best serialized candidate was **1491 depth / 845 CX** (overwrite bit 1).
The full screen is in `artifacts/comparator_oracle/three_plus_three/screen.json`.
The best measured row remains k=28, overwrite bit 1 at 1491/845; k=35,
overwrite bit 2 reaches 1504/866. Failed overwrite choices are recorded.
This fails the <=70-depth GO threshold decisively and closes the tested 3+3
affine-isometry lowering; no x-side synthesis or kernel integration was done.
