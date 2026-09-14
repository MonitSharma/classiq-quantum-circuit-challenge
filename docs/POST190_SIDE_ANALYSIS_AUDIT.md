# Audit of the five supplied side-analysis notes

The notes are useful search history, but do not establish a global 187-depth
floor, exclude Boolean encoders, or identify the private leaderboard algorithms.
The protected result remains 190/857/18. No new full oracle was produced here.

## Reproduced counterexamples and local facts

`src/post190_side_analysis_audit.py` records results in
`artifacts/post190_side_analysis_audit/counterexamples.json`:

* Eighteen independent Rz gates compile to depth one in u3/cx. Therefore
  floor(W/3) is not a universal per-layer rotation limit. Gate occupancy can
  give bounds when a justified total CX count accompanies a specified circuit
  representation, but a distinct CX per rotation cannot simply be assumed.
* A six-input conjunction depends on all six input bits, yet computes into a
  clean target with five shared AND nodes: RCCX(0,1,6), RCCX(2,3,7),
  RCCX(4,5,8), RCCX(6,7,9), RCCX(9,8,10). The native circuit has depth 17 and
  15 CX, on 11 wires. All 64 clean-ancilla basis inputs have the correct target
  bit. Intermediate garbage is retained; the actual inverse can clean it after
  diagonal phase application. This is an illustrative predicate, not the logo.
  Six-variable dependence does not force a 64-rotation UCR implementation.
* The full logo truth matrix has GF(2) rank ten. Eleven rectangle products can
  be a valid decomposition, but they are not a proof of rank eleven or a
  requirement to materialize 22 separate predicates simultaneously.
* The protected QASM has 857 CX and 784 u3 gates. Its saved kernel phase recipe
  has 63 nonconstant terms. The notes' K=117 and 885-rotation model does not
  describe this package; a comparison must first reconcile representations.

Additional unsupported deductions in the notes:

* AND counts of 97 or 156 for selected constructions are upper bounds from
  those constructions, not impossibility certificates for better factorizations.
  Counts must also be lowered and scheduled with the six-clean-ancilla limit.
  Exact Toffoli and RCCX costs are different; CX/6 cannot recover an AND count.
* Repeated annealing convergence does not prove a global minimum for K, class
  labels, or joint-feature compression. A nonzero annealing residual is a failed
  search, not an UNSAT certificate.
* Claimed exhaustive subspace results, if independently verified, constrain
  their precisely specified encoding families. They cannot close all Boolean,
  in-place, or mixed-coordinate encodings.
* Depth/CX pairs do not uniquely distinguish lookup, arithmetic, or mixed
  circuits. A failed Classiq model also does not prove no different Classiq
  model could compile well. The reported SDK failure is not independently
  reproduced in this audit.
* A three-bit side descriptor alone cannot distinguish eleven full-logo row
  or column classes. A level-function proposal must retain a tag, specify a
  restricted disk-only domain, or explain how mode/rectangle information survives.

## Concrete continuation started

`src/post190_free_label_xag.py` searches shared six-input XOR/AND networks
with three affine output bits, retaining raw masks 32 on y and 48 on x.
The three-bit labels are solver variables, constant within each (raw,class)
cell and distinct between classes sharing the raw tag. This changes the
fixed-output synthesis problem: labels can adapt to cheaper Boolean logic.
It is a Boolean feasibility screen, not an 18-qubit quantum construction.

Bounds of four, five, and six AND nodes were tested on each side, with eight
seconds per bound. All six calls returned UNKNOWN (timeout). No UNSAT or
optimality claim follows. The first probe produced no witness. The report is
`artifacts/post190_free_label_xag_v1/report.json`.
A positive-control regression with a two-bit affine classifier passes, including
independent evaluation of all 64 inputs (`tests/test_post190_free_label_xag.py`).
All jobs finished; no background search is running.

## Recommended decision criterion

Keep shared Boolean level/class encoding open, but judge it by a complete
native circuit, not an inferred rotation count or AND count. Try the protected
labels first to retain the known kernel, then allow relabeling while charging
its kernel cost. For any Boolean witness, account for affine CNOTs, live
registers, garbage cleanup, and the full phase action before promotion.

A sufficient illustrative sub-140 budget is an encoder of at most 50 layers
(on all 18 wires, with the two sides scheduled together), a compatible phase
stage of at most 35, and the encoder's actual inverse: at most 135 in total.
Neither component has been found at that budget. This is a target, not a
prediction. The first milestone is a verified cheaper encoder/complete oracle,
not another assertion that the existing architecture is globally optimal.
