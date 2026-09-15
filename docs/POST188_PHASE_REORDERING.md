# Verified 186 / 855 / 18 through phase reordering and scheduling

September 15, 2026. The protected local package is `artifacts/186/`, SHA
`5e7f8f165928e965cc47d5b697def0681a79aa6432b8d94302374fd071f25ac6`.
All earlier packages and the original notebook are preserved. This improves
188/855 locally and the screenshot's 190/857 submission. It would beat the
188-depth entry in that screenshot, but no live rank or submission was checked.
The screenshot's leader is 137/561/18; rank one remains unfinished.

## Successful change

`src/post188_phasepoly_probe.py` expands U3 gates into H and Rz operations,
checking each replacement as a full one-qubit operator up to global phase.
It invokes the public [PhasePoly implementation](https://github.com/ruadapt/PhasePoly)
at commit `03c278fe522bd509e4a3c9ba814c0e09239a4279` in rotation-merging mode.
See its [research paper](https://arxiv.org/abs/2506.20624). The external checkout
and optional `depq` dependency are under `/tmp`; the workspace environment was
not replaced. The adapter now also handles general Euler angles, with numerical
angles retained when they are not rational multiples of pi.

For the 188 source, PhasePoly reports unchanged Rz and CX counts. Its reordered
output exposes different native U3 fusions: U3 count falls from 773 to 771,
although emitted native depth initially worsens to 199. Exact commuting-gate
scheduling then reaches 186/855. A further native fusion removes one U3, and
another exact schedule preserves 186/855. Thus the result comes from the
combination of phase-level ordering, native fusion, and scheduling; it is not
evidence of a smaller phase-polynomial support.

Relevant artifacts:

- `post188_phasepoly_merge_v1/`: reordered 199/855 source, fully verified.
- `post188_phasepoly_exact_v1/`: first 186/855 and its native-fused file.
- `post186_native_exact_v1/`: final 186/855, U3 770, fixed-graph optimum.
- `post186_replay_v1/`: deterministic, identical-hash replay and verification.

CP-SAT optimality is limited to each fixed gate list and conservative
commutation graph. It is not a lower bound on all implementations of the logo.

## Verification

- Exact serialized package: 186 depth, 855 CX, 770 U3, 18 qubits.
- All 4,096 promised basis inputs pass: max error 6.26e-15, ancilla error zero,
  accumulated discarded-amplitude bound 1.95e-14.
- Five dense-superposition checks pass: max error 2.93e-16, ancilla amplitude
  5.90e-17, normalization error 9.77e-15.
- QMOD parsing matches all 1,625 oracle gates. Its preparation harness is not
  part of the scored QASM.
- Package replay matches the final SHA and independently passes all inputs.
- Six focused tests pass, covering phase conversion, modular lift invariance,
  conservative commutation, and native output wire identities.

Replay from the workspace root, choosing a new output directory:

```sh
.venv/bin/python src/build_rescheduled_oracle.py --package artifacts/186 --outdir /tmp/classiq-186-replay --verify
```

## Structural probes and negative results

These experiments address costs beyond fixed-gate scheduling. None has yet
produced a sub-140 oracle.

1. **Joint modular phases for three-output loaders.**
   `src/post188_joint_phase_loader.py` permits full-turn Boolean cube additions
   involving multiple loaded bits and removes address-only phases, which cancel
   in an exact compute/phase/inverse construction. Two 45-second searches each
   reached 173 nonconstant terms. Native loaders measured y124/268 and x129/270,
   worse than the existing 77-layer loaders. All 512 address/target phase values
   and all 64 promised loader outputs pass their respective checks.
2. **Revisit sparse code labels with a newly synthesized kernel.**
   `src/post188_sparse_code_revisit.py` actually builds the saved balanced and
   frontier encoders, then uses reweighted LP phase synthesis on reachable code
   words. Their loaders are 71–76 layers; the kernels need 91–124 terms in these
   runs. Full circuits measure 209/860, 217/856, 218/869, 219/799, 219/823, and
   224/820. All six full oracles pass all 4,096 inputs. Faster lookup alone did
   not offset the phase-kernel cost.
3. **Depth-weighted whole-circuit Pauli synthesis.**
   After converting to the required H/Rz/CX gate set and materializing implicit
   swaps, one greedy setting measures 726/1150 and a sets strategy 1432/1253.
   These are unverified depth regressions, not accepted circuits. Another
   greedy setting returns a verified 188/855. Full peephole optimization of
   186 produces verified 195/855; exact rescheduling returns to 186/855.
4. **Smaller Pauli-synthesis instances.**
   Full 512-by-512 operator comparisons validate both outputs, but the protected
   y loader regresses 77/193 to 184/222, and a sparse y loader regresses 71/151
   to 107/149. Lower CX in the latter does not mean lower depth.
5. **Bounded cross-block PhasePoly synthesis.**
   The row-heap runs with larger and smaller search settings were externally
   stopped after 100 and 90 seconds without a final circuit. These are timeouts,
   not impossibility results. The initial naive gate conversion was also worse
   and was superseded by the checked explicit Euler converter.

The older `POST196_SLACK_PROFILE.md` assertion that every saved balanced code
has floor 77 is not reproduced by the current correct loaded-bit extraction
(`code >> 1`): the three balanced entries have per-side heuristic bounds
(68,67), (68,66), and (71,72). Their measured native encoders above are the
relevant usable results. This observation does not invalidate the 77-layer
measurement for the protected codes or prove a globally optimal alternative.

## Reusing the new method on previous candidates

Rotation-level reordering followed by exact scheduling gives:

| Original source | Reordered native | Exact scheduled |
|---|---:|---:|
| Protected 190/857 | 193/857 | 188/857 |
| Protected 192/862 | 194/862 | 189/862 |
| Protected 193/853 | 195/853 | 188/853 |
| Protected 196/858 | 198/858 | 191/858 |

All eight intermediate and scheduled oracles pass the exhaustive verifier.
The 188/853 circuit is useful as a lower-CX alternative, but 186/855 wins the
primary depth metric. Reapplying rotation merging to the first 186 circuit
also returns to a fixed-graph optimum of 186.

The saved nonlinear 200/859 circuit also improves to a verified **195/859**
after rotation reordering and exact scheduling (`post186_nonlinear_exact_v1/`).
It still trails the protected package.

`src/post186_split_schedule.py` exposes H and phase factors directly, represents
each as a native gate, and tries 256 conservative schedules before fusion.
Best stochastic output is 188/855; exact scheduling and further fusion reach
186/855 through one path and 187/855 through another. Exact scheduling of the
native inverse of the protected oracle also stays at 186/855. These final
variants all pass the exhaustive verifier. They provide an internal alternative
to external phase reordering, but no further depth gain in this run.

## Remaining work

The 49-layer gap to the screenshot's leader is still substantial. The old
77-layer compute and inverse stages motivate replacing their representation,
but they are not a global depth lower bound after cross-stage rewrites. A
new encoder must be assessed together with its reachable-state phase kernel
and restoration cost. The direct Boolean 139-layer template remains unsolved
and must not be presented as a candidate.

All jobs from this continuation have finished. No background optimization,
leaderboard monitor, or submission is scheduled.
