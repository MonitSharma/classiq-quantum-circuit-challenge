# Phase weaving audit

This deterministic audit tests whether already-saved partial reversible
trajectories expose protected kernel phase information transiently. It does
not synthesize new trajectories or modify `artifacts/190/`.

The actual `artifacts/190/kernel.qasm` phase network was parsed symbolically,
tracking GF(2) wire parities through every CX and accumulating each U3 phase.
It contains **63 nonzero parity-phase terms**. The coefficient histogram is
`1/4:2, 15/8:12, 1/8:15, 7/4:2, 1/16:14, 31/16:12, 3/16:3, 29/16:3`;
parity weights are `{1:3, 2:10, 3:17, 4:17, 5:11, 6:5}`. All 256 kernel
descriptor basis states match the extracted phase polynomial and final linear
map up to one common global phase.

## Coverage results

| Trajectory | Prefix depth convention | Side parities ever available | Independent protected terms |
|---|---:|---:|---:|
| Y quotient index 0 (Y38) | 38 | 3/15: masks 1,4,5 | — |
| X quotient index 2 (X41) | 41 | 1/15: mask 1 | 3/63 jointly |

The Y quotient indices 1 and 2 have the same 3/15 mask set. X quotient
indices 0 and 1 have the same 1/15 mask set. Comparison-B Y indices 0–2
expose 3/15 masks, `{1,2,3}`, but are substantially deeper.

For the priority Y38/X41 pair, only 3 of 63 protected terms are independently
coverable. Weighted absolute-angle coverage is **1/117**. The 1,221-cell
checkpoint grid has a maximum of 3 tappable terms at any cell and a union of
3 terms. The same 3/63 result holds for the simple forward+inverse union
audit; all other protected masks are listed in
`artifacts/post190_phase_weave/global_coverage.json`.

The exact priority-pair artifacts are under
`artifacts/post190_phase_weave/`: kernel polynomial, descriptor parities,
trajectory coverage, global coverage, and monotone schedule statistics.

This fails the brief’s 30/63 go/no-go threshold, so trajectory-weighted phase
re-synthesis and woven-oracle construction are not justified for these saved
trajectories. The strongest next experiment is a different trajectory family
whose parity objective is explicit from the start; deeper refinements of the
current residual-XAG or phase-weaving paths should not be launched from these
coverage numbers alone.

Reproduce with:

```sh
PYTHONPATH=src .venv/bin/python src/post190_phase_weave_audit.py --outdir artifacts/post190_phase_weave
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_post190_relative_xag.py tests/test_post190_relative_depth2.py
```
