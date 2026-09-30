# Code-search and kernel-variant tools (paths assume the /work layout; edit before use)
- labeval.py / kerneval.py: loader-frame proxy and kernel-term estimate for a class labeling.
- labanneal.py / jointanneal.py / maskanneal*.py: label anneals (x only; joint x+y with kernel; other parity masks).
- newlab.py / bestframe.py / gensupw.py / gensupc.py: build frames and kernel phase arrays for a labeling / conditioning.
- kgenw.py: phase sparsification with a cost on terms needing the late Lx1 wire.
- pairhelp.py (+ kbeam_t3h.c, build with -DN=9/10): FEM kernel with helper (garbage) wires.
- wiperm.py (+ kbeam_t3p.c, HOMEV env): FEM kernel ending in a permutation of code roles.
- liveness.py: which loader ops/wires still matter at the end.
None of these reached depth 114; see docs/technical-report.md, section 6.
