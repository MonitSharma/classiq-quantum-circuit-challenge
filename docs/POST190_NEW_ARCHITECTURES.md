# Structural oracle research after 190

The protected best remains **190 depth / 857 CX / 18 qubits**, SHA
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.
No improved complete circuit, sub-140 circuit, or winning submission was
produced in this continuation. No optimization jobs remain running.

The current encoder stages each take 77 layers. Their nominal stage budget is
154 before the kernel. This motivates replacing the implementation; it is not
a general lower bound covering arbitrary cross-stage algebraic rewrites.

## Direct Boolean phase oracle: a concrete alternative

`src/post190_direct_boolean_template.py` eliminates both lookup loaders and the
eight-wire phase kernel. It seeks a reversible circuit E whose physical wire
17 contains the logo predicate after computation, for all 4,096 inputs with
the six ancillas initially zero. Other intermediate wires may hold arbitrary
garbage. The oracle is E, then Z on wire 17, then the actual inverse of E.
That restores all coordinates and ancillas and implements the required phase.

The implemented template contains:

- Six nonlinear stages, each allowing six disjoint relative-phase Toffolis.
- Three layers of disjoint CNOTs between consecutive nonlinear stages.
- A fixed initial product layer pairing adjacent input wires into the six
  ancillas; later stages choose their wire assignments and enabled gates.

One parallel RCCX stage lowers to at most nine U3/CX layers, checked locally.
If this template can implement the predicate, its constructive depth ceiling is

`2 * (6 * 9 + 5 * 3) + 1 = 139`.

**139 is a conditional template bound, not a synthesized logo circuit.** The
template may be too restrictive. No claim is made that six stages suffice.
It uses 18 wires throughout. Relative phases are legitimate here because E
is a computational-basis permutation up to phases and the actual E inverse
cancels those phases around Z.

The counterexample-guided Z3 search found a circuit satisfying 16 sampled logo
inputs in 2.82 seconds. Checking all 4,096 rejected it: 2,047 inputs failed.
After adding counterexamples, the solve with 32 samples timed out after about
31 seconds. A second, full-CNF/CaDiCaL route was externally stopped at 45 seconds
without a solver conclusion. Neither result is UNSAT or a valid submission.

The positive-control test fixes the later gates off and asks for the known
predicate y4 AND y5. Its extracted circuit agrees on all 4,096 inputs. A separate
operator check validates RCCX/Z/inverse phase cleanup. Three focused tests pass.

Files:

- `artifacts/post190_direct_boolean_v1/report.json`
- `artifacts/post190_direct_boolean_cadical_wall.json`
- `src/post190_direct_boolean_cadical.py` (must use `src/run_bounded.py`)
- `tests/test_post190_new_architectures.py`

## Low-degree Boolean descriptors with class splitting

The previous encodings assign labels to raw-tag/class cells. This probe instead
allows different points of a class to receive different three-bit labels,
provided different classes never collide after including the retained raw tag.
The output bits are constrained directly through their algebraic normal forms.

For the existing raw masks (row 32 and column 48):

| Maximum output degree | Row side | Column side |
|---|---|---|
| 3 | UNSAT, 0.10 seconds | UNSAT, 0.86 seconds |
| 4 | SAT, 0.53 seconds | SAT, 7.13 seconds |

The degree-four truth-table witnesses are independently checked on all 64
inputs per side. Degree four is therefore attainable, and the solver excludes
degree at most three **for these fixed raw tags, three loaded bits, and this
class-separation model**. This does not exclude other raw tags or circuit
architectures. Output affine symmetry breaking maps three distinct labels to
0, 1, 2 and preserves polynomial degree.

This does not supply fast loaders. The witnesses have 35 and 42 distinct
nonlinear monomials before factoring. Attempts to reduce a weighted monomial
cost timed out after 20 seconds per side; those thresholds are not lower bounds.
Also, these particular codes occupy all 16 descriptor values per side, leaving
no unreachable eight-wire kernel states. Their principal Boolean phase spectrum
has all 255 nonconstant terms, versus the current 63-term representation.
Thus the encoder and kernel must be designed together; low degree by itself
does not establish a depth improvement.

Witnesses and diagnostics: `artifacts/post190_split_degree4_v1/`.
Degree-three solver results: `artifacts/post190_split_degree3_v1/`.
Sparsity attempt: `artifacts/post190_sparse_degree4_v1/`.

## Mixed-coordinate descriptors

`src/post190_mixed_descriptors.py` checked all 462 unordered six/six bit
partitions under 433 individually applied transformations: identity, 72
cross-axis CNOTs, and 360 Toffolis with one control on each axis. This is
200,046 partition/transformation pairs.

The screen permits arbitrary functions of each half and counts the distinct
rows and columns of its Boolean table. At most 16 on each side is a necessary
condition for two independent four-bit descriptors. Eighty-five cases pass
that count test, but every one retains the original x/y partition. No mixed
partition passes in this tested family. This does not cover arbitrary affine
changes, multiple-gate preprocessors, or descriptors with overlapping inputs.

Report: `artifacts/post190_mixed_descriptors_v1/report.json`.

## Direction supported by these results

For sub-140, prioritize a direct reversible Boolean implementation that uses
coordinate wires as intermediate storage, with cleanup by the actual inverse.
The 139-layer template gives an explicit resource target and a full-input
acceptance test. The unsolved work is Boolean circuit synthesis into that
resource budget. The template is a research route, not evidence that the
leader's private circuit uses this method or that it will win the challenge.
