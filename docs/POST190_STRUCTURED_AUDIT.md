# Structured class-coordinate audit

The repository reproduces the proposed direct structured coordinates exactly.
The 11x11 class matrix has 35 ones and GF(2) rank 10; its nonzero 10x10 core
is also rank 10. The supplied rank-10 Y/X cut seed reproduces the core with
zero mismatches.

The structured four-bit truth tables match the expected values and ANF
profiles exactly:

- Y: `0x3f4f97eb3e6800`, `0xc01807007000`, `0x3fe000ff8000`,
  `0x3fffffe0000000`; degrees/monomials `(5,28),(5,18),(5,14),(6,8)`.
- X: `0xc1967cd07fffffc`, `0x1c1ce00e00000000`, `0x3e01ff007fffffc`,
  `0x2003fffff8000000`; degrees/monomials `(5,32),(5,16),(6,28),(5,12)`.
- The structured comparator identity has **0 mismatches** over all 4,096
  coordinates.

The exact normalized class-cut distributions are Y `(degree 4: 15, degree 5:
496, degree 6: 512)` and X `(7, 504, 512)`. Degree-≤5 cuts span rank 9 on
each side, confirming that any rank-10 class-cut basis needs a degree-6
direction on both sides.

The full Boolean witness spans intersect the ten-dimensional class-cut spaces
in dimension 3 on both sides, while the saved shallow Y38/X41 trajectory
unions intersect them in dimension 1 per side. These are exact span checks and
support abandoning those trajectories for rank-10 feature harvesting.

The zero-filled direct-relabel kernel screen is not evidence against direct
labels: the 35-care-bit relation has odd weight, forcing all 255 Walsh
coefficients to be nonzero after zero fill. The prior 16×16 kernel portfolio
was therefore discarded as biased, not treated as exhaustive.

Machine-readable results are in `artifacts/post190_structured_audit/report.json`.
No protected artifact was modified.
