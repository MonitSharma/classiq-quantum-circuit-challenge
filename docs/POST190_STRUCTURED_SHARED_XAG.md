# Structured shared-XAG audit

The structured four-output targets were screened with exact 64-bit Z3
BitVec constraints. The six 7-AND, three-stage patterns requested for each
side were tested: `1+3+3`, `2+2+3`, `2+3+2`, `3+1+3`, `3+2+2`, and `3+3+1`.
All Y and X runs returned `UNKNOWN` at the five-second bounded limit. These
are not UNSAT results and do not establish a lower bound beyond the already
proved seven-AND/three-stage algebraic floor.

No exact shared witness entered the promotion region, so no physical lowering
was launched. The machine-readable results are in
`artifacts/post190_structured_shared_xag/report.json`.

The repository audit found `src/sub140_projection_anneal.py`, which mutates a
fixed-length sequence, but each trial recomputes semantics from the initial
state and scores class-separation conflicts. It does not cache boundaries or
replay a changed interior layer through an existing suffix, and it is not an
equivalent implementation of the requested complete-schedule optimizer.

The protected `artifacts/190/` package remains untouched. The next defensible
step, if continued, is a narrowly scoped whole-schedule prototype with cached
interior replay—not a larger prefix beam—and with exact full-domain semantic
regressions before optimization.
