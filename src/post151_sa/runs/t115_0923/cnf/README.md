# Depth-114 x-loader tail SAT instances (Sept 24–25)

Depth 114 needs an x loader with Lx1 ready at 43, px at 42 and x12 at 43 (Lx0 up to 38). See
`docs/technical-report.md`, section 6. These instances ask whether the last
12 layers (32–43) of an existing x loader can be re-synthesized to reach that profile. Target 0 (Lx0)
closes at layer 31 in every champion-lineage x loader, so these instances decide whether that lineage
can reach 114.

Kissat could not decide any of them within our time budget (up to 1.5 h per run). They need a machine
that can run for many hours without interruption.

| file | source loader (window from layer 31, 12 layers) | constraints |
|---|---|---|
| `r36_31.cnf` (build it, see below) | `x_r36_1_q2_req256.pkl` | full: Lx1, x12 ≤ 43, px ≤ 42, Lx0 ≤ 38 |
| `champ_31.cnf` (build it) | `x_champ_req256.pkl` | full |
| `r36_31_rA.cnf.gz` | r36 | relaxed: only Lx1, x12 ≤ 43 |
| `r36_31_rB.cnf.gz` / `r36_31_rC.cnf.gz` | r36 | rA + px ≤ 42 / rA + Lx0 ≤ 38 |
| `t1only.cnf.gz` / `t2only.cnf.gz` | r36 | only target 1 / only target 2 (the other treated as done) |
| `pf31_k3.cnf.gz` | r36 | full, plus 3 free CX layers before layer 32 (Lx0 wire untouched) |

If any relaxation (rA, t1only, t2only, pf31_k3) is **UNSAT**, the full instance is UNSAT too. That
would mean a depth-43 x loader needs target 0 to close by layer 30.

Build the full instances (takes about a minute; the result is identical to the original CNF, md5 `d032dc34…` for r36):
```
cd src/post151_sa
python3 tail115/tailcnf.py runs/t115_0923/cnf/x_r36_1_q2_req256.pkl 31 12 '{"idle":{"0":1,"1":5}}' r36_31.cnf
python3 tail115/tailcnf.py runs/t115_0923/cnf/x_champ_req256.pkl 31 12 '{"idle":{"0":1,"1":5}}' champ_31.cnf
```
How to run (for hours; the `kissat` binary from Homebrew or a source build):
```
gunzip -k r36_31_rA.cnf.gz
kissat r36_31_rA.cnf > r36_31_rA.sol      # prints "s SATISFIABLE" or "s UNSATISFIABLE" at the end
```
If an instance is SATISFIABLE, decode it into a loader (use the same arguments that built it):
```
python3 src/post151_sa/tail115/tailcnf.py <this dir>/x_r36_1_q2_req256.pkl 31 12 '{"idle":{"0":1,"1":5}}' r36_31.cnf r36_31.sol
```
(rA: spec `'{}'`; rB: `'{"idle":{"0":1}}'`; rC: `'{"idle":{"1":5}}'`; pf31_k3: add a 7th argument `3`.
`t1only`/`t2only` are only useful as UNSAT tests; they were built by a separate script and can't be decoded.)
The decoded loader `r36_31.cnf.pkl` must then pass the FEM kernel beam at T=114 with y `yw005_3`,
then the MILP, and then exhaustive verification (tail115/paireval.py and everify.py).
