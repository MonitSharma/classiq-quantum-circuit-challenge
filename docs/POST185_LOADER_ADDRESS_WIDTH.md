# Where the 185 depth is, and why label/kernel tuning cannot reach rank one

> **Subsequent audit, September 16:** The numerical experiments below are
> historical notes, not an architecture-wide impossibility proof. The saved
> `artifacts/185/kernel.qasm` measures **38 layers / 87 CX**, not 29 layers.
> Adding separately measured block depths does not prove a 156-layer floor
> after joint synthesis. Five-variable loaders were independently reproduced,
> and twelve complete follow-up circuits were compiled and verified. See
> `docs/POST185_FIVE_ADDRESS_AUDIT.md` for the measured results and limitations.

September 16. Protected best is unchanged at **185 / 854 / 18**. Nothing here
produced a new circuit; this note records measurements that bound what the
current architecture can reach, so later work is not spent on dead levers.

## 1. The depth budget is the two loaders

`two_stage_oracle` is loader(x) ‖ loader(y) → 8-wire kernel → inverse loaders.
Measured with the repo's own primitives (`distributed_ucry.structured_ucry`,
best of several seeds and of `sparse` / `open_walk` / plain, then
`transpile(optimization_level=3, qubits_initially_zero=False)`):

| block | depth | CX |
|---|---:|---:|
| y loader, current labels | 78 | 204 |
| x loader, current labels | 77–78 | ~200 |
| 8-wire kernel (integer-ANF lift, `post258_kernel_schedule.synth`) | ~29 | ~90 |

`2 x 78 + 29 = 185`. **The loaders are ~84% of the depth**, and the
architecture's floor is therefore about **156** even with a free kernel.
A 137-depth result is unreachable here by any amount of label or kernel tuning.

## 2. Loader depth is set by ADDRESS WIDTH, not by payload

Two measurements on the same primitive:

| loaded bits (6-bit address) | depth | CX |
|---|---:|---:|
| 1 | 71 | 72 |
| 2 | 78 | 156 |
| 3 | 78 | 204 |

| address width (3 loaded bits) | depth | CX |
|---|---:|---:|
| 6 variables | 78 | 200 |
| 5 variables | 63 | 126 |
| 4 variables | 49 | 76 |

So reducing how many bits are loaded buys nothing. Reducing how many
*variables the label depends on* is the only lever inside this primitive.

## 3. Exhaustive frame searches: the 4-bit code forces a 6-variable label

All searches below are over affine frames (free code bits are parities, i.e.
CX-only, hence free) and over all valid label assignments.

- **Can a label bit ignore a direction?** For a 4-bit code (one free parity +
  a 3-bit label) the label would need `<= 8` values on the quotient by some
  direction `d`. Minimum achievable is **10** (x) and **14** (y). No frame works.
- **Trade loaded bits for free parities?** With 2 free parities a 2-bit label
  needs `<= 4` classes per cell; the minimum over all frames is **5** (x) and
  **6** (y). With 3 free parities a 1-bit label needs `<= 2`; minimum is **4**
  for both. Neither works.
- **5-bit code (2 free parities + a 3-bit label of 5 variables).** This *does*
  exist — max class signature per cell is 7 (x, mask 48, coset pairing
  `(0,55,16,39)`) and 8 (y, mask 32, pairing `(0,16,32,48)`) — and it would cut
  each loader to 63. But the resulting 10-wire kernel has **244 ANF terms**
  (degrees concentrated at 5–7) against **25** for the 8-wire kernel. The kernel
  cost far exceeds the 2 x 15 layers saved. Net loss.
- **6-bit code (no loader at all).** The logo function's ANF over the 12
  coordinate bits has **886 monomials** (degrees peaking at 6–8). Dead.

The current 4-bit class code with an 8-wire kernel is a genuine sweet spot.

## 4. Label choice cannot shorten the multiplexer

The loader is a distributed uniformly-controlled Ry. Its Gray-walk length is
governed by the Walsh support of the label bits, and a label bit with odd
support has all 64 Walsh coefficients nonzero. The current labels have supports
`(47, 64, 64)` for x and `(46, 64, 64)` for y.

Enumerating *all* cell subsets (2^14 per parity mask) and all valid injective
triples gives a minimum **total** Walsh support of **94** for y (against 174
now). Measured effect on the loader: **78 → 72**. A per-stage balance proxy
(which predicts the current labels at 84 against a measured 78) was annealed
down to 66–70; the measured depth stayed at **77**. The depth is set by
`structured_ucry`'s fixed four-stage basis-change structure, not by coefficient
sparsity.

Also measured as negative results:
- pytket `FullPeepholeOptimise` / `CliffordSimp` on a loader block: 78 → 78–81.
- Qiskit `synth_cnot_phase_aam` (GraySynth) on the same phase-gadget set:
  depth 432.
- A generalised sparsity-adaptive staged emitter written here (arbitrary stage
  count, `change_basis` transitions): depth 154. `structured_ucry`'s special
  three-layer stage transition is worth roughly 11 layers per stage and should
  not be replaced by generic PMH lowering.

## 5. What is left

Only a **Boolean AND-network loader** can break 156, which is the conclusion
`LEVEL_COMPARATOR.md` already reached for the level codes; this note confirms it
for the class-code architecture and quantifies the target: an encoder at
**<= 55 layers** keeps the 8-wire kernel and lands near 140; **<= 40** lands
near 110.

The obstruction remains register peak, not AND count. One route not yet tested
is to break the x/y symmetry in time rather than in wires:

- The x code needs only **one** ancilla if its four code bits are placed on the
  x data wires: class sizes give `sum(ceil(size/8)) = 14 <= 16` codes for both
  sides, so a fibre of at most eight fits the three remaining data wires.
- That allows a **sequential** schedule where the x encoder runs on 12 wires
  (6 data + 6 ancillas) and the y encoder afterwards on 11. Twelve wires remove
  the register peak that blocks AND-network synthesis.
- The cost is serialisation: the budget becomes `2*(Lx + Ly) + K` instead of
  `2*max(Lx,Ly) + K`, so both encoders must come in near **30 layers** to beat
  185, and near 25 to reach rank one. Whether Bennett cleanup of the five
  ancillas the y encoder needs back can be paid inside that budget is the open
  question, and it is the first thing to measure.

Nothing in this note was submitted, and `artifacts/185` is untouched.

## 6. Addendum: nonlinear frames cannot shrink the address beyond one variable

Measured loader depth for narrower addresses: 3 variables → 28, 2 → 8.
A 3-variable label after a two-batch Toffoli frame would give about
`2*(14+28)+29 = 113`, so this was checked before building.

It is impossible, even for nonlinear (Toffoli) data-wire bijections. If the
3-bit label ignores a `d`-dimensional set of directions and the code is
`(parity, label)`, every class restricted to one parity is a union of fibres
of size `2^(d-1)`. For `d >= 2` every class must therefore split into two even
parts. x class `[2,26]` has 25 members and y classes have odd sizes too, so no
bijection works. Bijections preserve class sizes. `d = 1` is allowed (63-layer
loader) but costs at least one RCCX batch (~7 layers) on both sides: roughly
`2*(7+63)+29 = 169`, far from 127.

## 7. Follow-up round (September 16): all negative, 185 unchanged

New code: `src/post185_qcorr_oracle.py` (generic label->oracle pipeline, exhaustively
verified control at 242), `src/post185_qcorr_search.py`, `src/post185_k10_anneal.py`,
`src/post185_joint_label_anneal.py`, `src/post185_label_build.py`.

- **Toffoli-corrected narrow lookup** (`label = U(coset) XOR q`, q a product of two
  affine forms, up to three RCCX): exact GF(2) search finds **no** frame for
  lookup addresses of 4 or 2 variables on either axis. A 5-variable address also
  has no solution with node-constant labels.
- **10-wire kernel with annealed labels**: best 122 ANF terms, degrees mostly 5–7,
  against 25 for the 8-wire kernel. Dead.
- **Integer-lifted loader tables** (ANF lift): Walsh support not reduced; loader 78.
- **Joint label anneal** (encoder depth via `post224_relative_lookup.relative` +
  kernel cost): relative encoders stay at **76–77** for every labeling. Kernel
  cost drops 67 -> 64 (21 terms). In the same untuned pipeline the full oracle
  goes 216 -> **214** (both exhaustively verified). The recorded 218 kernel recipe
  (43-layer kernel) is much stronger than a plain ANF lift (61–64), so any label
  change must be pushed through cube additions + beam + bridge rewrites; the
  expected gain is a few layers, not 58.
- **Beam phase-polynomial scheduler on the loader** (`post218_beam_phase.psynth`
  on the 174 loader gadgets): depth **129**, far worse than the structured 77.
- **Classiq synthesis of the level identity**: comparators need 20 qubits;
  lookup-phase form raised an internal Classiq error. Not pursued.
