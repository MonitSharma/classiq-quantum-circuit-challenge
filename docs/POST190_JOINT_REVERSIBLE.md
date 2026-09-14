# Joint reversible encoding with free labels

September 15, 2026. Protected best remains **190 / 857 / 18**. No new full
encoder witness or improved submission was found in these bounded experiments.

## Implemented

`src/post190_joint_reversible.py` searches actual nine-wire reversible circuits,
with six arbitrary input wires and three initially clean wires. Its four
observed descriptor wires are the previous raw slot and three ancillas. The
other five wires may carry reversible garbage. The raw slot no longer needs
to retain a particular coordinate parity unless `--split` is requested.

The default contract assigns a free four-bit label to each row/column class.
The `--loose` contract also permits multiple labels within a class, while
forbidding collisions between different classes. X/CX/RCCX operations are
modeled on actual wire values; no abstract retirement assumption is used.
No free affine output gauge is imposed, since a general affine map has native
cost. Symmetries only order commuting gates within disjoint layers.

Class-constant constraints were simplified to one equality group per class
and distinct representative codes. This is equivalent to the pairwise model.
Split mode groups by class and raw value, whose low output bit is constrained.

Four nonlinear matching stages plus two CX matching layers in each gap have
a conservative explicit native budget of 48 layers; six stages have budget 70.
These are template budgets, not found encoder depths. Relative phases are
allowed only through an actual compute/diagonal/inverse sandwich.

## Bounded results

| Artifact suffix | Side | Stages | Contract | Inputs | Result |
| --- | --- | ---: | --- | --- | --- |
| joint_y4 | y | 4 | class constant | 64 | 20-second timeout |
| joint_x4_loose | x | 4 | splitting allowed | 64 | 20-second timeout |
| joint_y6_cegis | y | 6 | splitting allowed | 12 then 21 | sampled SAT rejected; timeout |
| joint_x6_cegis | x | 6 | class constant | 12 then 20 | sampled SAT rejected; timeout |
| joint_y6_grouped | y | 6 | grouped class constant | 64 | 45-second timeout |
| joint_x6_grouped | x | 6 | grouped class constant | 64 | 45-second timeout |

Directories have prefix `artifacts/post190_`. The sampled y candidate failed
63 full-domain inputs and x failed 64. These counts mark inputs participating
in a collision or constancy violation, not independently wrong output bits.
Both candidates were rejected. No UNSAT conclusion or architecture-wide lower
bound follows from the timeouts. All newly launched processes finished.

## New-label composition is verified

`src/post190_joint_compose.py` reads the actual output basis permutation of each
encoder on all 64 inputs, verifies class separation, and derives the phase
truth table on all reachable descriptor pairs. It builds a fresh diagonal
kernel with care-set LP synthesis and beam scheduling, checks its operator,
then composes the encoder, kernel and actual inverse. It does not reuse the
protected permuted kernel with incompatible labels.

Successful full encoder witnesses automatically go through this path and
`src/exhaustive_verify.py` on serialized QASM before being treated as results.

Control using existing encoders with an independently synthesized kernel:

- `artifacts/post190_joint_compose_control/oracle.qasm`
- **201 depth / 866 CX / 18 wires**, 67 phase terms, kernel depth 48.
- All 4096 inputs pass, max error 7.57e-15, zero ancilla error.
- SHA `7a819a891d84c181282ec687203ad52e257d7b46e2b80a7e7c22956222aa4db6`.
- This is a correctness control, **not an improved circuit**.

Three focused tests cover positive synthesis, quantum inversion, collision
versus constancy checks, and the full-logo care-set contract. They pass.
Protected QASM SHA is unchanged:
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.

## Remaining limitation

The search now measures the right object, but finding a full-domain witness is
still unresolved. Merely increasing an AND bound or obtaining a sampled SAT
result is not an improvement. New labels also require measuring the new phase
kernel: a cheaper encoder may create a more expensive middle. Neither sub-140
nor rank one has been achieved or ruled out by this work.
