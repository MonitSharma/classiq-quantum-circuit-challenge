# Verified depth-258 oracle: distributed lookup phases

September 12, 2026. The best verified local oracle is now **258 depth / 1188 CX /
18 qubits**, down from 456/1140. This is a 43.4% depth reduction. The observed
183-depth target remains unfinished; no submission or rank-one claim is made.

## Protected deliverables

Directory: `artifacts/258/`.

* `distributed_level_258.qasm`: authoritative standalone oracle.
* `distributed_level_258.exhaustive.json`: all 4096 input columns verified.
* `distributed_level_258.verification.json`: independent Aer dense-state checks.
* `distributed_level_258.qmod`: a gate-for-gate matching oracle function plus
  the original style of Hadamard synthesis harness in `main`.
* `kernel.qasm`: the exact six-qubit 13-depth kernel used by the builder.
* `recipe.json`: the code choices and six lookup settings.
* `manifest.json`, `audit.json`: hashes, gate correspondence, and replay checks.

QASM SHA-256:

`b2a2e8ac6a6d7ee2c2e4ec11bcca4b4ba4fe54aab15b11c71236efcecdca3066`

The exhaustive report has maximum error **1.296e-14**, ancilla error **0**, and
discarded-amplitude bound **2.326e-14**. It compares all basis columns using one
shared global phase. The protected 456, 524, and original notebook are unchanged.

## What was unnecessarily restricted

The earlier ladder implementation put lookup rotations on three output
ancillas and used the six coordinate wires only as controls. Full Walsh support
then forced 64 rotations and roughly 64 CX operations on an individual output.

Full support does not require those phases to be evaluated on the same physical
wire. A coordinate wire may temporarily hold a parity involving an ancilla,
receive a phase, and be restored. That is allowed by the problem specification.
This work exploits exactly that freedom. It keeps the successful two-level-
comparison identity rather than inventing a new geometric decomposition.

This is also a concrete correction to the earlier broad claim that the lookup
architecture was exhausted. The old fixed-wire lower bounds remain correct for
the old gate placement; they do not exclude this different implementation.

## Exact lookup identity

For each output t, write its angle table as

`theta_t(z) = sum_s theta_hat_t(s) (-1)^(s dot z)`.

An address-controlled Rz lookup is the product of parity rotations

`Rz(theta_hat_t(s)) on the parity (t XOR (s dot z))`.

The rotations commute. A reversible linear circuit can therefore move these
parities onto different physical wires. Rx conjugation on the output changes
the rotation axis back to Y: chronologically, apply Rx(pi/2), the diagonal
network, then Rx(-pi/2). This realizes the intended uniformly controlled Ry.

The construction is an exact operator identity for arbitrary values on all
nine participating wires. It does not assume the targets or borrowed coordinate
wires are clean. This is stronger than the reachable-state condition needed by
the oracle and makes the merged middle lookup safe.

## Four structured parity bases

Split the six coordinate bits into three low controls and three high variables
`h0,h1,h2`. Combine the three high wires and three output wires `t0,t1,t2`
into six phase hosts.

For each output i, the high-coordinate part of a desired parity is one of eight
values `t_i XOR subset(h0,h1,h2)`. There are 24 such parities across three
outputs. We visit them using four bases, each holding six independent desired
parities:

`t_i XOR shift_i` and `h_i XOR t_i XOR shift_i`, for i=0,1,2.

For each i, `shift_i` walks the other two high bits in two-bit Gray order.
The pair of hosts covers the presence/absence of h_i; four shifts cover the
remaining high masks. Each basis therefore supports six parallel three-control
Rz sweeps over the low bits.

The first implementation partitioned the 24 parities into random invertible
bases and used a generic linear compiler. It already produced a verified
391-depth oracle. The decisive next step was making the basis changes explicit.

To move between structured bases:

1. CX each output into its paired high wire, restoring all three original high
   variables in one layer.
2. Apply a cyclic high-to-output CX layer to change all three shifts.
3. Recopy the outputs into the paired high wires in one layer.

Thus a transition takes **three layers**. The generic PMH linear compiler took
11–12 layers on these same structured transitions in the diagnostic. Initial
encoding takes one layer; final restoration takes two for this Gray path.

Within each basis, the six phase hosts use shifted low-bit Gray orders. Their
operations interleave on three low controls. The code also supports sparse
walks, but these did not beat the dense carried-walk construction for the
selected final recipe.

## Carry the low-bit parity instead of closing every walk

A three-bit Gray walk visits all eight masks in seven edges. The old version
added an eighth edge to return every host to its original parity.

Here paired high/output hosts have the same final low-bit parity. When the
output is XORed back into the high wire, those low-bit contributions cancel.
The output's remaining low-bit parity can be carried to the next basis and
accounted for in the next angle lookup. After four walks, the offsets cancel.

This removes 24 CX operations per fully dense lookup and reduces its measured
depth from 82 to 78. The final selected components are 77–78 depth. All six
were checked as serialized nine-qubit operators on all 512 basis inputs, with
maximum errors below 3.2e-15.

## The phase kernel was not minimal either

For the selected codebooks, the six code bits `(a,b,c,d,e,f)` use the polynomial

`a*f XOR a*b*d XOR a*c*e XOR b*d*f XOR c*e*f`.

Factor it as

`a*f XOR (a XOR f)*(b*d XOR c*e)`.

Apply CZ(a,f), temporarily replace f by f XOR a, apply CCZ(f,b,d) and
CCZ(f,c,e), and restore f. This is exact on all 64 code states, not only the
36 reachable pairs. Ordinary native lowering reduces the kernel from 27 to
20 depth.

A bounded parity-network search reduces the complete kernel further to **13
depth / 15 CX**. It uses the integer phase lift

`f*(b*d + c*e)`

inside the temporary basis. Using the sum instead of Boolean XOR changes the
phase by integer multiples of 2*pi and exposes 13 nonconstant parity terms.
Using the Boolean 0/1 truth table directly had 31 terms and was a poorer search
representation. The search tracks actual per-wire gate depth, applies each
required phase when its parity becomes available, then restores the full
linear basis. Every retained kernel improvement was checked against the
original six-variable polynomial after QASM serialization.

The search used beam 1000 and fourteen CX expansion steps. It is not an
optimality proof. A separate restricted one-CCZ-plus-quadratic screen over 1395
three-dimensional linear subspaces found no solution for these fixed codebooks;
that diagnostic does not exclude other codes or general kernel circuits.

## Full-oracle assembly and measured progression

The codebooks are the original cheap-kernel pair:

* y level subsets: `(56,52,38)`.
* x level subsets: `(20,34,56)`.

The six selected lookup seeds are y `(0,1,0)` and x `(2,1,0)`, all structured
open Gray walks. Each side loads pass-one angles, applies the angle difference
for pass two, and finally applies negative pass-two angles. The two sides run
on disjoint nine-wire sets; the phase kernel couples their code outputs.

| Verified complete circuit | Depth | CX | Main change |
|---|---:|---:|---|
| Previous protected level circuit | 456 | 1140 | Target-hosted dense lookup ladders |
| Distributed arbitrary bases | 391 | 1534 | Coordinate wires also host lookup phases |
| Structured basis transitions | 297 | 1340 | Explicit three-layer transitions |
| Carried walks and factored kernel | 272 | 1186 | Avoid repeated parity restoration; two cubic terms |
| Final package | **258** | **1188** | Exact 13-layer kernel |

The output-frame screen tested 28 unordered invertible output bases per side,
12 construction seeds and two walk modes, with a small native shortlist per
stage. The best retained final result uses the identity output frames. Its
purpose was to test a real reduction in phase work, not merely another
transpiler-seed sweep. The intermediate 286-depth frame candidates were not
promoted as verified milestones.

Clifford and full-peephole rewrites of the new 272 circuit gave 274 and 284;
they were not improvements. The earlier split-code direction-invariance probe
timed out without a witness and is not an impossibility result.

## Verification, QMOD, and replay

`tests/test_distributed_ucry.py` passes five focused tests: three arbitrary-angle
lookup variants and two full kernel operator checks. The lookup tests include
negative angles, non-Boolean angles, and zero entries; they do not merely check
the intended classical output labels.

The packaged QASM passed exhaustive verification again after copying. A fresh
builder replay in a separate directory reproduced its SHA exactly. The QMOD
oracle's 2274 calls were checked in order against every QASM gate, including
wire indices and parameters; the maximum parameter difference is zero.

The QMOD was created locally through the installed Classiq SDK, without a new
login, cloud synthesis, or submission. Its `main` includes twelve Hadamards
solely as a synthesis harness. The authoritative QASM contains none of those
preparation gates. Re-synthesizing the QMOD may produce a different schedule;
the packaged QASM is the verified and scored artifact.

Replay from the workspace root, using a new output directory:

```sh
.venv/bin/python src/build_distributed_best.py \
  --recipe artifacts/258/recipe.json \
  --kernel artifacts/258/kernel.qasm \
  --outdir /tmp/classiq_distributed_replay_new \
  --verify-components
.venv/bin/python src/exhaustive_verify.py \
  /tmp/classiq_distributed_replay_new/distributed_level_258.qasm
.venv/bin/python -m pytest -q tests/test_distributed_ucry.py
```

## Remaining gap

The new circuit has 1086 U3 gates and 1188 CX gates. Its maximum wire-touch
count is 239, down from 389 in the 456 artifact; its occupied-wire-slot lower
bound is 193. These are bounds on this fixed gate implementation, not universal
oracle bounds. Reordering the present gates alone cannot reach 183.

The two kernels now account for about 26 staged layers. The three lookup stages
dominate again, each around 78. Under the same staged cost model, matching 183
would require average lookup depth around 52, or another reduction in the
number or structure of stages. Further kernel-only improvements cannot close
the entire gap.

The concrete new research direction is now phase placement and whole-stage
construction using all available wires. The previous conclusion that arbitrary
coordinates had to remain untouched inside the lookup was an implementation
restriction, and removing it delivered a substantial verified improvement.
The final oracle must still implement the challenge's prescribed phase action.

## Executed notebook

[`classiq-distributed-lookup-258.ipynb`](../classiq-distributed-lookup-258.ipynb)
contains the package checks and exact replay. All code cells were executed
successfully, including component verification and a fresh 4096-input exhaustive
check. The original notebook is preserved.
