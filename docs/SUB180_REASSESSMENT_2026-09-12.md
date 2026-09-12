# Sub-180 reassessment, September 12, 2026

The user reports a verified leaderboard result of depth 183 with no public
implementation. This is a user-provided benchmark, not a newly fetched ranking.
Sub-180 remains the target; no circuit at that depth was produced in this work.

## Verified circuit status

The best documented depth remains **456 / 1140 CX / 18 qubits** at
`artifacts/456/level_merged_456.qasm`. Its SHA matches the existing exhaustive
report, checked again today. Depth is primary, so it supersedes 524 for the
depth objective despite having more CX. Both artifacts remain preserved.

The previously unverified `artifacts/level_sparse.qasm` was checked with
`src/exhaustive_verify.py`: all 4096 basis inputs pass, depth **472**, CX 1128,
maximum error 2.2649e-14, ancilla error 3.1666e-15. SHA:
`962a2253cf2c0f688405b41a549d62eafb8e4a1c7c5d59d9e1db4e21b9ebbc7e`.
Its new matching report is `artifacts/level_sparse.exhaustive.json`.
It is a verified negative result, not a new best.

## Exact exclusion of the proposed degree-3 v2 code

`LEVEL_COMPARATOR.md` suggested completing degree-3, three-bit encodings with
multiple codewords for the large class. Partial signature calculations did
not establish a fully separating code. The new screen closes this proposal
for **v2**, even without restricting which level classes may split.

Reasoning:

1. There are six nonempty levels and eight three-bit codewords. Disjoint
   codeword sets therefore allow at most two levels to use multiple codes.
2. Enumerate all 15 pairs of potentially split levels. On the other four
   levels, each output polynomial must be constant. These are linear
   constraints on its 42 degree-at-most-three ANF coefficients.
3. For 14 pairs, linear elimination finds two inputs from different levels
   that every permitted polynomial evaluates identically. Those pairs cannot
   yield a separating code at any choice of three outputs in that space.
4. Only split levels (1,5) survive. The complete three-output disjointness SAT
   problem for that pair is UNSAT. An independent formulation with the raw
   ANF coefficients and Glucose3 agrees with the reduced CaDiCaL formulation.

Both SAT formulations use the same justified output symmetry: the codes for
three singleton levels can be fixed to 000, 001, 010 because an invertible
output affine transformation maps any three distinct codewords to these.
It preserves Boolean degree and codeword-set disjointness.

This is a solver-backed exhaustive exclusion for this encoding model, not a
machine-checked proof certificate. The independent tests also check every
linear collision witness using a separate elimination implementation.
A bounded u1 screen leaves one case unresolved; its timeout is not UNSAT.
The unpartitioned original v2 SAT model was interrupted without a conclusion.

Consequences: at least one output of a three-bit v2 level encoding must have
Boolean degree >=4. This does **not** rule out degree-4 encoders, shallow
quantum circuits, four-bit codes, shared encoders, or another representation.
It supplies no general lower bound of 180, 183, or 456 on oracle depth.

## Reproduction

```sh
.venv/bin/python src/level_split_code_screen.py --name v2 --seconds 30 --out artifacts/level_split_v2_screen.json
.venv/bin/python src/level_split_code_screen.py --name u1 --seconds 8 --out artifacts/level_split_u1_screen.json
.venv/bin/python -m pytest -q tests/test_level_split_code_screen.py
.venv/bin/python src/exhaustive_verify.py artifacts/level_sparse.qasm
```

The focused test suite passes: 3 tests. Original notebook, circuit generators,
and verified best QASM were not edited.

## Implication for the next experiment

Do not continue the degree-3 three-bit level-code search or rerun the existing
multiplexer cleanup. Any follow-up needs a different concrete construction,
with all encoder, phase, and restoration costs counted before a large search.
Degree >=4 by itself is neither a useful depth estimate nor a reason to reject
an encoder. A shallow native construction remains the missing deliverable.
The older claims that 456 is a universal multiplexer floor, the natural split
is optimal, or only AND-network encoders could improve it should be read as
heuristic statements about tested designs, not proven exclusions.
