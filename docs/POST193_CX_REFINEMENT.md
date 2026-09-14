# Depth unchanged; CX improved to 853

The September 14 continuation did **not** lower depth below 193. It improved
the tie-breaker from 857 to **853 CX**, at the same width of 18 qubits. The new
package is `artifacts/193_cx853/`; the original `artifacts/193/` remains intact.
No rank-one result or submission is claimed.

The exact standalone QASM SHA is
`4dbd4993f7d1e807b5ae2908f9580d70070f247a4496140b858f08c95ce82709`.
All 4,096 basis inputs pass with a common global phase, maximum error 7.56e-15,
zero ancilla error, and discarded-amplitude bound 1.41e-14.
Five dense random superpositions also pass (maximum error 2.21e-16), and
fourteen targeted tests pass.

## Construction change

The previous phase beam selected its completed state using restoration to the
identity. Only afterward did a separate search relax restoration to an ancilla
permutation. The new `finalize` callback in `post218_beam_phase.psynth` allows
the final beam selection itself to use the relaxed output order. Its default
behavior is unchanged. The callback is only invoked on complete phase schedules.
The caller is responsible for the new output contract and rewired uncomputation.

With the same 63-term phase representation, seed 37, beam 64, branch 14, alpha
5 and time weight 0.35, this yields a **40-depth / 85-CX** kernel. The full
oracle initially reaches 193 / 855. Reselecting the loaders gives the final
193 / 853 circuit: row seed **298**, column seed **506**, with the same seeds
for their inverses. The kernel's physical ancilla permutation is retained.

The search also considered different forward and inverse loader schedules.
They may be combined without an extra phase correction only when their
input-dependent phases agree up to a global phase. The new symbolic gauge
calculation checks that condition on all 64 coordinate values and is separately
tested against numerical statevectors. The winning circuit happened to use
the same forward/inverse seeds; asymmetric scheduling did not provide a depth
gain in the sampled set.

## Completed search scope

| Search | Scope | Result |
|---|---|---|
| Reselect loaders for original 193 kernel | 256 seeds per side; 285 Pareto combinations | No gain |
| Ancilla ordering inside beam finalization | 64 seeds; 300 suffix samples per completed beam state | 193 / 855 |
| Same search with nonuniform input arrival times | 32 seeds | No gain |
| Reselect loaders for new kernel | 256 seeds per side; 285 Pareto combinations | No gain |
| Further suffix search on new kernel | 30,000 samples; 80 native compilations | Same 193 / 855 SHA |
| Phase-compatible loader pairs | 512 seeds per side; 32,038 compatible pairs; 600 compiled candidates across three predicted depths | 193 / 853 |
| Warm reweighted phase LP | 48 restarts, six iterations each | Support remained 63 |
| Modular phase/nullspace moves | 1,200 steps, 1,529 moves | Support remained 63 |
| Round native angles to their intended dyadic grid | Full 193 / 855 circuit | Identical SHA |

These are bounded experiments, not depth or support lower bounds. The earlier
160-seed compatible-loader pilot produced 193 / 854 and is superseded.

The matching QMOD contains all 1,636 standalone oracle gates. Its main includes
the twelve preparation Hadamards; the standalone QASM does not. Compiler replay
uses the saved kernel, class codes, loader seeds and physical mapping through
`src/build_permuted_oracle_package.py`. The original phase-search recipe is
also included for provenance. No optimization jobs or monitors remain running.
