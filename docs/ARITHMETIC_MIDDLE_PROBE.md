# Measured arithmetic components and frame-model audit

The protected logo oracle remains **196 depth / 858 CX / 18 qubits**. This
checkpoint improves an arithmetic comparator component; it does not produce a
new logo oracle or establish a rank-one construction.

## Verified improvement: phase comparator with parallel prefixes

For four-bit radius r, folded magnitude v and sign s, the required comparison
is `v <= r-s`. Carry-out of `r + ~v + (1-s)` implements that condition.
An optional enable bit controls its phase. Coordinates and helper qubits must
be restored, with one common global phase over the checked input domain.

| Four-bit comparator | Depth | CX | Clean helpers |
|---|---:|---:|---:|
| Relative-phase ripple, unenabled | 65 | 39 | 0 |
| Remove the final carry computation, unenabled | 57 | 35 | 0 |
| **Parallel prefixes, unenabled** | **25** | 44 | 2 |
| Relative-phase ripple, enabled | 69 | 41 | 0 |
| Remove final carry computation, enabled | 63 | 43 | 0 |
| **Parallel prefixes, enabled** | **36** | 70 | 2 |

The gain trades extra CX and two clean helpers for much shorter depth, which
is the competition's primary metric. The prefix implementations were serialized
as standalone U3/CX QASM and then checked on **all 512 unenabled or 1,024 enabled
inputs**, including helper restoration and a common global phase. Maximum
errors are 1.09e-15 and 1.24e-15. Reports and hashes are under
`artifacts/post196_prefix_comparator/`; reproduce using
`.venv/bin/python src/post196_prefix_comparator.py --outdir /tmp/fresh_prefix_probe` with a nonexistent output directory.
These QASMs implement comparators, **not the logo oracle**; they are not challenge
submission artifacts. Protected artifacts/196 is unchanged.

### Construction

Let `P_i = r_i XOR ~v_i` and `c = 1-s`. Compute differences
`D_c=r_0 XOR c` and `D_i=r_(i+1) XOR r_i`, preserving reversibility.
With two clean helpers compute `t=P_3 P_2` and `u=P_1 P_0` in parallel.
The final carry is

```
r_3 XOR P_3 D_2 XOR t D_1 XOR t P_1 D_0 XOR t u D_c.
```

Apply this as a diagonal phase, optionally multiplied by the enable bit, and
invert the actual compute circuit. Relative phases from the AND gates cancel.
This avoids propagating a carry through all four positions. The chosen diagonal
kernels are 10 layers unenabled and 21 enabled; native cross-boundary
simplification gives the full 25- and 36-layer components above.

## Reflection shared by both disks

For x in [32,63], `x XOR 31 = 95-x`. Thus a y5-controlled XOR of the five low x
bits maps the disk centered at 55 to one centered at 40; the disk centered at
40 is unchanged when y5=0. Both disks lie in that upper x half.

Subtracting eight modulo 32 aligns the low coordinate with the shared center.
A sign-controlled one's complement gives a magnitude v that is |d|-1 on the
negative side and d on the positive side, explaining the `r-s` comparison.
The combined reversible reflection, subtraction and fold compiles to **10 depth
/ 10 CX** and was checked on all 128 inputs. It must be inverted after the
phase work. See `post196_arithmetic_probe.py` and its artifact reports.
The rectangles must be handled in original coordinates or transformed
consistently; this reflection alone is not a complete oracle.

## What this does and does not establish about a full hybrid

Using the side analysis's *unverified* 63-layer y-loader estimate, a modular
sum for load/unload, fold/unfold and the enabled comparator is already
`2*63 + 2*10 + 36 = 182`. This still excludes radius/mode decoding, the r=8
exception, rectangle/bridge phases and any opportunities for shared work.
It therefore does not defend a sub-140 hybrid. It does replace one of the
weak estimated costs by a substantially improved measured component.

A competitive integration needs to reduce the y preparation cost and/or share
mode, radius and rectangle work with the comparison. Three code bits cannot
naively hold all four binary radius bits plus the row modes. Resource accounting
must include that encoding issue; the three unused ancillas cannot simultaneously
serve as arbitrary radius bits, mode flags and comparator helpers.

## The new frame model remains a heuristic bound

The Held-Karp table correctly measures individual minimum closed tours. The
maximum of host workload and average source workload does not solve the joint
scheduling problem. A concrete fixed-frame counterexample has all six hosts
visiting low masks {0,1}. Every closed tour uses low wire 0 twice. The stated
formula returns **4**, but that one wire alone needs **12 CX operations**; an
explicit schedule takes 13 layers. Reproduce with
`src/post196_frame_model_audit.py`.

Consequently matching 77 at one point is calibration, not proof of exactness
for all tables. The 68-versus-70 point already demonstrates a gap. Annealing
also does not certify a global optimum over labels or GL(6,2). That group has
20,158,709,760 elements, and the inspected basis search additionally pins a raw
parity. No exhaustive enumeration or optimality certificate was provided.
The revised 'unconditional' formula still uses the invalid general kernel
bound `3*T_K/8`, addressed in `POST196_FLOOR_AUDIT.md`.

Finally, leaderboard CX counts do not identify private implementations as
arithmetic. They motivate testing lower-CX methods but cannot establish which
algorithm was used. No community contact, cloud submission, background job or
leaderboard-monitoring automation was started here.
