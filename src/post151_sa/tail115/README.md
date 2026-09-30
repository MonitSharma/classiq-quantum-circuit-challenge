# tail115 tools (2026-09-23)
- kbeam_t3.c: 3-type kernel beam (rotations ZS/ZD, controls CS/CD, targets XS/XD) + DUMPD/DUMPN/DUMPF state dump + auto hash size. Build: gcc -O3 -march=native -DN=8 -o kbeam_t3 kbeam_t3.c -lm
- ktail.py: exact SAT completion (kissat) of a kernel state in the calibrated model.
- drive.py / split.py: run ktail on a beam dump (split.py = parallel parts).
- fromk.py: replay the first d layers of a kernel schedule, then SAT-complete at a target T.
- evco.py: kernel schedule + phase array -> assemble -> canc.simplify -> exact MILP (smilp).
- everify.py: qiskit-free exhaustive verifier (same algorithm as classiq_synth.core.verify).
- satwin3.py / tailsat3.py: loader tail SAT with notarget/idle/close_by constraints.
Paths assume a fixed layout (/work/classiq for this repository, /work/k for run directories, /tmp/kissat for
the solver); edit them before use.
See docs/technical-report.md (sections 3.3, 3.4 and 6).

## Sept 24 additions
- paireval.py: loader pair -> FEM kernel beam -> assemble -> canc -> MILP. Run with `STRICT=1 ZOCC=1 FUSE=1`.
  Fixed: an opening H at layer 1 is no longer counted as a closing H.
- wifem.py: FEM what-if from a real pair with per-wire overrides (plan index 0 Ly0, 1 Ly2, 2 py, 3 Ly1,
  4 Lx0, 5 px, 6 x12, 7 Lx1). Keys: dec, inc (whole wire), xdec (CX window only), zdec (rotation window
  only), xsdec / xddec (loader side / unloader side CX window only), or raw rdy/zs/zd/occmax.
  It now sets the FEM env itself. Runs before Sept 24 without FUSE=1 were stricter than FEM.
- wimix.py: FEM what-if with loader pair A at the start and the mirror of pair B at the end.
- pscreen.py: FEM kernel-beam screen (no MILP) over lists of x and y loaders; writes JSON lines.
- prof.py: prints rdy / srdy / hz / ST / CX per loader.
- satwin3.py: `max_cx` (sequential-counter at-most-K on CX) and `KOPTS` env for kissat options.
- kpeep.py: kernel CX peephole. It re-synthesizes interior kernel windows with SAT (satwin3, NV=8, max_cx) and keeps a
  change only if the exact MILP still gives T. This produced 115 / 568 CX (artifacts/115).
- kpeep2.py: kpeep with boundary windows (per-wire FEM CX/rotation windows), several window sizes, and explicit
  schedule JSON input/output.
- tailcnf.py: builds (or decodes a kissat model for) the x-loader tail SAT used for the depth-114 search, including
  the free-layer relaxation. See runs/t115_0923/cnf/README.md.
