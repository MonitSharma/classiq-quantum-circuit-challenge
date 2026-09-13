# Continued search from depth 218

September 13, 2026. The verified best is now **196 depth / 858 CX / 18 qubits**,
packaged in `artifacts/196/`. The intermediate 198 package is also kept. Sub-180 was **not** reached. This document records
what produced the improvement, and — more usefully for whoever continues — the
measurements that place a floor on the current two-stage architecture.

## Verified improvement: schedule the kernel with a beam, not a greedy layer

The oracle is unchanged in structure: two relative-phase loaders in parallel,
one eight-wire diagonal kernel, then the inverse loaders. The class codes and
the integer phase lift are exactly those recorded in `artifacts/218/`.

What changed is the scheduler for the eight-wire phase polynomial.
`post258_kernel_schedule.synth` scores one CX layer at a time from immediate
hits plus a one-step lookahead. `src/post218_beam_phase.py` keeps a beam of
partial schedules and ranks them with an exact potential: writing every
outstanding parity in the current wire basis, a `CX(a, b)` changes coordinate
`a` by `c_a ^= c_b`, so the change in the total coordinate weight is
`n_b - 2 M[a][b]` where `M` is the coordinate coincidence matrix and `n_b` the
number of outstanding parities using coordinate `b`. Both are one small matrix
product, which is what makes a beam affordable.

| Kernel scheduler | Depth | CX |
|---|---|---|
| recorded 218 kernel | 66 | 123 |
| `synth`, 400 seeds | 61 | 128 |
| beam, 120 seeds x 5 configurations | 45 | 88 |
| beam, 400 seeds x 3 configurations | **43** | **89** |

The kernel is checked against `diag(exp(i*phases))` up to global phase at
6.2e-15 before it is used. Re-selecting the encoder seeds (y 99, x 155
rather than y 11, x 151) against the new kernel gives the remaining layers.

Oracle SHA `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`.
All 4096 coordinate basis inputs pass with one shared global phase, maximum
error 9.03e-15 and zero ancilla error; five dense random states pass at
2.54e-16. `src/build_two_stage_196.py` rebuilds the exact file, and the QMOD
matches all 1647 gates.

### Methodological caution

The first version of the beam scheduler reported kernels at 45–49 layers that
were **wrong**: the search loop exited when the *best* beam state was complete,
and the final selection then also considered states that still had outstanding
parities, emitting circuits that silently omitted rotations. It was caught by
the `Operator` check in the build script, not by the depth numbers, which looked
plausible. Any depth reported by a new scheduler in this workspace should be
treated as meaningless until the exact diagonal check has run.

## Where this architecture's floor is

The loader is now the whole cost: 77 + 43 + 77 with almost no cross-boundary
merging. Two independent arguments say 77 is close to optimal for it.

*Wire-slot counting.* The loader is a nine-wire phase polynomial, Rx- (or H-)
conjugated on the three outputs, whose parities each contain exactly one output
variable. The current codes need 174 and 175 Walsh terms. Each rotation needs
its parity on a wire, and consecutive distinct parities on a wire need at least
one CX, so at least `174 - 9` CX gates are required. A CX occupies two wires and
an Rz one, giving at least `(2 * 165 + 174) / 9 = 56` layers.

*Host/source counting.* A parity `a_t ^ mask` can only sit on a wire whose value
carries exactly one output variable, so wires holding pure control parities —
the ones that supply the CX deltas — cannot host rotations. With `s` pure
sources and `9 - s` hosts, a host does `2 * 192 / (9 - s)` operations, and a
layer can hold at most `min(s, 9 - s, 4)` CX gates. `s = 3` minimises the
maximum of the two, at 64 operations per host, plus roughly 13 layers of frame
skeleton: about 77.

Measured: 77 for both sides over 260 `post224_relative_lookup` seeds and 130
seeds of the new `src/post218_bank_loader.py`, which schedules each frame with
exact shortest closed Hamming tours and conflict-aware interleaving. The bank
loader does help when the tables are sparse (67 -> 62) but is worse when they
are dense (77 -> 83), because for full frames the fixed cyclic-shift staggering
in `structured_ucry` is already optimal.

So the architecture bottoms out near `2 * 77 + kernel`, and the kernel is now
43. Getting materially below 190 requires changing the loader's job, not its
schedule — which is exactly what the failed variants below were trying to do.

## Implemented experiments that did not improve the result

| Experiment | Measured result | Scope |
|---|---|---|
| Walsh-sparse class codes (annealed labels) | loader terms 174 -> 94 / 175 -> 101, loaders 77 -> 62, but kernel 69 -> 170 terms and 45 -> 99 layers; total 223 | Confirms and quantifies the earlier "rebuilt kernels consumed the savings" note |
| Unstructured beam scheduling of the loader | 132 and 126 | The generic potential does not find the output-copy structure |
| Beam scheduling with an ancilla-count guard | 70 and 74 | Still worse than 77; the guard prunes illegal states but not myopia |
| Joint code annealing against depth-calibrated costs | 9000 steps x 3 seeds from the 218 labels: no improvement on predicted 199.7 | The 218 labelling is a strong local optimum of `(loader terms, kernel terms)` |
| Kernel integer-lift re-search | 88 terms from the low-degree ANF base; the recorded 69-term lift was not beaten | My move set is weaker than `post221_kernel_cube_nulls`; not a proof that 69 is optimal |
| Two-frame loader feasibility (SAT) | 250 sampled independent direction triples per raw parity, all UNSAT | Not a complete enumeration of the 39060 triples |
| Three raw parities plus two loaded bits | loader terms 97 and 90, but reachable kernel inputs 837 of 1024, ANF degree 8, kernel 711 terms / 382 layers | Decisive: wider codes destroy the don't-care compression the kernel depends on |
| XOR symmetry of the class maps | best `v` leaves 20 of 64 rows mismatched; predicate best is 90 of 4096 | No exact five-bit quotient exists, so the lookup address cannot be narrowed this way |

### Why the two-frame idea was worth testing

In frame `f` of `structured_ucry`, host `i` can only carry Walsh masks whose
high part lies in `{shift_i, h_i ^ shift_i}`; running only the first two frames
restricts output `i` to masks with high part in `span{h_i, h_(i+1)}`, that is,
to a code bit that does not depend on the transformed coordinate `h_(i+2)` at
all. A two-frame loader would be roughly half as deep, which would be the
largest single saving available. `src/post218_two_frame_codes.py` encodes the
question as SAT — one instance per triple of independent directions — and every
sampled instance was unsatisfiable. Completing the enumeration would turn this
sample into a real exclusion; it is the cheapest open item here.

## Status

Sub-180 and rank one remain unresolved. The 218, 221, 222, 224 and earlier
packages are preserved and their hashes are unchanged. No cloud resynthesis or
challenge submission was performed, and no background optimiser or leaderboard
monitor is left running.
