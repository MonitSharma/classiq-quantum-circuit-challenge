# Improvement to 193 depth

September 14: the verified local best is **193 depth / 857 CX / 18 qubits**,
packaged with a matching literal QMOD in `artifacts/193/`. The standalone QASM
SHA is `5c00b23d9ea061b8b3062caac17ae2de0ab8457a4705ecc3eea8c1eed49a1bec`.
The prior 196 package is unchanged. Sub-140, sub-100 and rank one remain
unfinished. No submission or fresh leaderboard check was made this turn.

## What changed

The eight-wire kernel only encounters 182 of its 256 basis states. A new
reweighted L1 linear program chooses real phase coefficients subject to exact
equalities on those states. It explores both the old integer phase lift and the
principal Boolean 0/1 phase lift, with 48 randomized restarts and eight weight
updates each. The best candidate has **63 nonconstant terms**, against 69 in
the old kernel. It comes from the Boolean lift at restart 25. This is a
heuristic sparse representation, not a minimal-support certificate.

Six beam seeds on each of ten shortlisted representations did not improve the
full circuit. A further 160 schedules of the 63-term representation found a
verified **195 / 857** circuit (seed 60, beam 64, branch 14, alpha 4, time weight
0.9). Its diagonal kernel has depth 42.

The second change is at the kernel exit. Instead of restoring the six code
ancillas to their original order, the new construction permits their physical
permutation and rewires the inverse encoders accordingly. All coordinate wires
remain fixed. Because the inverse encoders clear the ancillas, their final
permutation has no effect on the required subspace. This is explicit circuit
wiring, not ignored transpiler layout metadata.

Applying this freedom to the 63-term seed-47 schedule reduces the complete
oracle to **193 / 857**. The kernel has 41 layers and 87 CX, including a
12-CX final linear network. The uncompute mapping, indexed by original physical
wire, is `[0,1,2,3,4,5,6,7,8,9,10,11,13,16,14,15,17,12]`.
Its kernel is therefore phase plus permutation, not a standalone diagonal
oracle. `src/build_two_stage_193.py` checks this mapping and reproduces the
exact QASM hash from the saved recipe.

## Bounded negative results

| Experiment | Scope | Best complete result |
|---|---|---:|
| Free ancilla order, old 69-term kernel | 20,000 suffix samples, 80 compilations | 197 / 857 |
| Arrival-aware beam scheduling, old spectrum | 24 seeds, both circuit directions | 202 / 868 |
| Care-state LP initial compilation | ten candidates, six seeds each | 197 / 860 |
| Free order applied to the 195 candidate | 20,000 suffix samples, 80 compilations | 194 / 862 |

The successful free-order search also used 20,000 suffix samples and 80 native
compilations. The fact that it helped the new kernel but not the old one is why
the two modifications were tested together. None of these searches establishes
an architectural depth floor.

## Correctness and preservation

The final serialized file passes `src/exhaustive_verify.py` on all 4,096 basis
inputs with a common global phase: maximum error 7.81e-15, ancilla error zero,
discarded-amplitude bound 1.33e-14. Replay gives the same SHA. The packaged QMOD
has exact correspondence to all 1,640 serialized gates; its main includes the
twelve-Hadamard preparation harness.

Five additional dense random states pass with maximum error 2.01e-16 and
ancilla amplitude at most 4.70e-17. Eleven targeted tests pass.

`src/post218_beam_phase.py` gained optional arrival and departure timings. Its
defaults retain the old behavior, and replay matches the protected 196 kernel
SHA. A regression test checks that nonuniform timings preserve the unitary.
The 193 tests additionally check the dyadic phases using integer arithmetic,
the kernel's phase-and-permutation operator, and the report/file SHA match.

All searches were bounded and have finished. No optimization or leaderboard
monitoring has been scheduled.
