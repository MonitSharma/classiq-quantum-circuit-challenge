# Continued search from depth 221

September 13, 2026. The current verified best is **218 depth / 897 CX / 18
qubits**, packaged in `artifacts/218/`. This is an intermediate improvement;
sub-180 and rank one remain unresolved. The user explicitly asked to continue
pursuing sub-180, rather than treat small improvements as completion.

## Verified improvement: change the integer phase representation

The Boolean kernel remains unchanged on every one of its 256 inputs. Adding
`2π * product(selected bits)` to its phase adds a full integer turn on every
basis state. We searched these equivalent representations, including products
absent from the original ANF. Coefficients were tracked exactly modulo 32 in
units of π/32 before native circuit synthesis.

`src/post221_kernel_cube_nulls.py` screened 6000 iterations over 1051 distinct
modular moves. Its selected 69-parity representation compiles at **66 depth /
123 CX**, with all 256 kernel columns checked. Joint encoder integration
produces **218/897/18**. All 221 Pareto timing pairs from 160 seeds per side
were compiled; the selected encoders are y seed 11 and x seed 151.

The oracle SHA is
`3a685c32ea0d78637be1a575c91e6c7d13db0efdbf37a8f794fb44e7fb024a88`.
The kernel SHA is
`49f80af03714de45797a4603e8cb8b8d008f97ed82582f68723d27d9bca9f352`.
All 4096 oracle basis columns pass with a common global phase, maximum error
8.83e-15 and zero ancilla error. Three independent dense inputs pass, maximum
error 2.43e-16. The literal QMOD matches all 1683 gates and parameters. Its main
has preparation Hadamards, absent from the standalone QASM. No cloud
resynthesis or challenge submission was performed.

`src/replay_two_stage_218.py` rebuilds both kernel and oracle, matches both
hashes, and runs exhaustive verification. The package includes the actual
modular phase vector in `kernel_recipe.json`; the old ANF in
`class_codes.json` specifies the same Boolean phase but is not the new lift.
The 221, 222 and 224 QASM hashes were rechecked and remain unchanged.

## Other implemented experiments

| Experiment | Measured result | Scope |
|---|---|---|
| Current-code signed encoder lifts | Best complete candidate 222/958; encoders remain 77 | No improvement; fewer rotations did not remove the critical CX dependencies |
| Enumerated spectral class bits | 875 y and 1225 x scalar choices; smallest separating triples have 94 and 100 Walsh terms | These are exact constant-cell choices, not all possible split-class codes |
| Sparse-code native builds | Isolated loaders as low as 67 and 68; best integrated tested circuit 246/818 | Rebuilt kernels consumed the savings; every proposed best in the family was exhaustively checked |
| Generic parity scheduling for those codes | Best tested full circuit 251/861 | No improvement over 218; generic scheduling did not beat the structured loader |
| Joint encoder/kernel Walsh-cost annealing | 20,000 steps; best compiled shortlist result 224/931 | Proxy improvement did not reliably predict whole-circuit depth |
| Signed weights of existing kernel monomials | 76 parity terms; best native kernel 72 | Narrower than the successful cube-addition family |
| Half-π null phases on unreachable rows/columns | 67 parity terms; best kernel 67/124 | 182 reachable kernel columns checked; does not preserve every unreachable column; not promoted |
| Affine-control Toffoli conjugations | 12,096 transformations screened; best corrected native kernel 82/151 | Shortlist of 20 compiled with six seeds; not a global exclusion |
| Whole-circuit TKET / PyZX rewrites | Best rewrite depth 224; others 234, 243, 304, 654, 1779, 1970 | No new best; reported worse-candidate metrics are not independent correctness certificates |

Raw evidence lives under `artifacts/post221_*` and
`artifacts/post218_half_phase_nulls_v1/`. Scripts use corresponding names.
The full 76-by-500 spectral-code pairing screen found kernel proxy cost 330;
that proxy is not a native depth. Initial generic/sparse native builds used
bounded 30-by-30 shortlists, not every one of those 38,000 pairs.

The whole-circuit experiments follow the supported transformations described
in [TKET's pass documentation](https://docs.quantinuum.com/tket/api-docs/passes.html)
and [PyZX's simplification documentation](https://pyzx.readthedocs.io/en/stable/notebooks/simplify.html).
Gate-count or T-count optimization is not evidence of improved U3/CX depth.
Initial Pauli-pass input-basis errors and a PyZX SWAP-import error were fixed
before rerunning those passes. The reruns completed and were worse.

## Larger resource-split and encoder tests

We explicitly tested the idea of replacing a loaded bit with another cheap
coordinate feature, freeing an ancilla. A reversible rank-two quadratic tag
combined with a linear second tag never gives four or fewer classes per
quarter: the best maximum was five for both sides. The follow-up enumerated
**1,661,600 y and 3,248,800 x** pairs of sequential reversible quadratic
coordinate updates, retaining the first tag while constructing the second.
None gave at most four classes in each quarter. These are exhaustive screens
of the generated family, not arbitrary nonlinear coordinate transformations.

An exact graph-parity screen of constant-cell encodings for all 67 viable y
and 131 viable x quadratic tags found no separating triple with three
independent affine-period directions. The largest scalar-option counts were
three for y and sixteen for x. It does not cover split-class encodings.

Two shallow-synthesis formulations also ran:

- Nine-wire affine/RCCX encoders, freeing the unused final affine rows: three
  nonlinear layers found partial witnesses, then returned UNKNOWN at 19
  samples after 55 seconds per side.
- A restricted first layer of three disjoint input products, followed by a
  free affine/nonlinear layer: partial witnesses at 11 and 19 samples, then
  UNKNOWN at 27 samples after 55 seconds per side.
- Six-wire reversible maps with three output tag bits, each bucket containing
  at most two classes: two nonlinear layers returned UNKNOWN at 55 seconds
  per side. This would permit a one-bit loader if solved, but no witness or
  circuit was produced.

UNKNOWN is not UNSAT. Partial sample witnesses are not valid encoders.
No low-depth result from these solver runs has been promoted.

## Kernel-degree synthesis: active extension

A new formulation jointly chooses class codes and a low-degree Boolean
kernel on reachable pairs. In its direct Z3 version, fixing current y codes
makes degree three and degree four UNSAT. Fixing x at degree four and freeing
both sides at degree three initially returned UNKNOWN at 55 seconds.

A second formulation eliminates the kernel coefficients. For fixed x codes,
each y-ANF coefficient must lie in the span of x monomials of complementary
degree. It uses 67 linear parity constraints at degree four plus one-hot y
label assignments. The Z3 version proved fixed-x degree-four UNSAT in about
50 seconds; a corrected CaDiCaL conversion independently returned UNSAT in
about 1.34 seconds. This is a constraint on the current fixed code, not a
proof that no degree-four encoding exists.

An initial CNF adapter failed to expand pseudo-Boolean cardinality atoms,
produced an invalid SAT indication, and failed witness extraction. That run
has no valid result. The corrected adapter expands cardinality constraints
and asserts that every CNF atom is a Boolean variable. A separate direct
adapter initially encountered unexpanded bit-vector distinctness; that was
caught by an assertion and corrected. No such result was used as a circuit
or proof. Both corrected adapters passed degree-five positive controls: their recovered
labels and polynomials were independently evaluated on every reachable pair.
The cofactor positive control solved in 1.22 seconds; the direct positive control
in 30.17 seconds. The rank test in `tests/test_post221_cofactor_projection.py`
independently confirms that the projected constraints span the full annihilator
of the direct low-degree evaluation space.

All 30 global three-bit x-code permutation representatives modulo affine output
transformations returned UNSAT at degree four. A further 100-second external
batch completed 77 of 168 conditional linear x-code frames, all UNSAT; it did
not complete the family. These statements fix the specified x code and allow
constant-cell y recoding. They do not exclude arbitrary simultaneous recoding,
split-class encodings, or non-diagonal kernels.

The unrestricted direct CaDiCaL degree-three/four runs exceeded the intended
in-process timeout and were explicitly terminated. They have no solver
conclusion. Native solver calls can prevent a Python timer thread from firing;
use `src/run_bounded.py` for an external process deadline in future runs.
No optimization processes are intentionally left running at this checkpoint.

An additional exact monomial-equivalence screen on all 4096 encoded states
found no lower-degree replacement for any of the 25 current kernel monomials
among positive monomials of degree at most five over all 18 wires. The few
alternatives mostly add a redundant x5 condition; this is not a general
all-feature phase-polynomial exclusion.

Six focused tests pass, including the new cofactor-space check, the clean-helper
phase tests, and existing arbitrary-input kernel checks.

The global sub-180 objective remains open. There is no scheduled background
optimizer or leaderboard monitor, and no rank claim is made from these local
results.
