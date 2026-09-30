# Numerical block resynthesis

These tools produced the depth-115 / 567-CX circuit (`artifacts/115/conditional_loader_115_cx567.qasm`). The method is
described in `docs/technical-report.md`, section 3.4. Paths inside the scripts assume the /work layout
(`/work/k` for run directories, `/work/classiq` for this repository); adjust them before running elsewhere.

| file | purpose |
|---|---|
| `blockscan.py` | QASM parser; maximal 2-qubit blocks and the KAK minimal-CX test |
| `convex3.py`, `convex4.py`, `block3.py` | maximal convex 3- and 4-qubit blocks in wire order |
| `inst3.py` | fewer-CX exact instantiation for each block (BFGS) |
| `ranks.py` | reachable-support rank of a block's input (don't-care freedom), by sparse simulation of all 4096 inputs |
| `resub.py` | substitute blocks, then `canc.simplify` and the exact MILP (`smilp`) at 114/115 |
| `depthsyn.py` | depth-aware version: enumerate sequences, sparsify 1q slots (none/Rz/Rx/U3), MILP |
| `fastfit.py` | analytic-gradient template fitter |
| `cblocks.py` | convex blocks in the commutation DAG (or in wire order with `wire=True`), block unitary, substitution |
| `dsloop.py` | iterated loop with exhaustive verification. Env: `WIRE=1` (wire-order blocks), `ORDER=rev`, `TWINS=1`, `SHARD=i/n` |
| `mkqmod.py` | literal Qmod transcription of a QASM file |

To reproduce 567, run `python3 depthsyn.py 73 9,11,13 3` with the 568 circuit as input.
