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
| `artifacts/comparator_oracle/y_loader/y_loader_esop_probe.qasm` | **555** | **358** | 18 |

This fails the primary y-loader criterion (`<=60` depth; `>75` kill).  It is a
loader-only diagnostic, not an oracle, and is not promoted.

## Decision

The exact identity is a useful classical description, but the first concrete
native lowering is decisively noncompetitive.  The x-loader, parallel-loader,
kernel, and full `L† K L` synthesis were not attempted because this lowering
already fails the hard criterion by nearly an order of magnitude.  The result
does not prove that every possible hand-designed classifier is impossible; it
closes this ESOP/relative-phase-MCX lowering.

The protected 524/950 artifact under `artifacts/524/` was not modified.

## Shared-address descriptor screen

The follow-up hypothesis was tested mathematically before circuit generation
by quotienting the exact 64x64 predicate into identical row and column
patterns.  The screen is implemented in
`src/shared_address_descriptor.py` and its complete report is
`artifacts/shared_address_descriptor/descriptor_report.json`.

There are exactly 11 row classes and 11 column classes, requiring at least
four binary descriptor bits on each side.  The descriptor is exact, but the
middle kernel remains dense after label optimization: over 2000 random row
and column label assignments, the best result had **86 ANF terms, 366 ANF
literals, degree 8, and 256/256 nonzero Walsh coefficients**.  This is a
mathematical screen only; no QROM circuit was claimed.

This does not prove that every shared-address QROM construction is
impossible, because a phase-tolerant traversal could exploit structure not
captured by an 8-bit ANF.  It does show that “compact descriptor” does not by
itself imply a <=55-depth kernel.  A future revisit would require an explicit
shared traversal primitive with native depth accounting, not another binary
label permutation or codeword-conditioned phase expansion.

## Whole-register semantic probe

The serialized probe was profiled in
`artifacts/comparator_oracle/y_loader/esop_failure_profile.json`.  It has 162
pre-lowering RCCX operations; after lowering, q0 is the most heavily used
wire (289 operations and 162 CX participations).  This confirms that the 555
depth is primarily a dirty-scratch/target serialization problem, not merely a
large number of independent gates.

`src/whole_register_y_search.py` then searched complete six-wire truth
signatures under X/CX/RCCX, scoring only four designated boundary outputs and
leaving two wires as unrestricted garbage.  With the initial fixed output
placement, a beam of 4000 states through 18 primitives did not reach the exact
boundary map; its best score was 157/256.  A broader arbitrary-output mapping
run was stopped for throughput before producing a report and is not treated as
negative evidence.  The search is therefore a bounded diagnostic, not a proof
against all reversible embeddings.

Nevertheless, the only completed native classifier is 555 depth, far beyond
the requested 70-depth kill threshold.  Per the experiment protocol, the
comparator architecture is **closed for this lowering**; x-side synthesis and
kernel integration were not started.
