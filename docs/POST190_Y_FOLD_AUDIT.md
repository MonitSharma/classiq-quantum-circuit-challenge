# Audit of y-fold cost and a narrower arithmetic alternative

Protected full oracle remains **190 / 857 / 18**. No sub-140 result.

`src/post190_y_fold_audit.py` independently reproduces the original **95 depth /
71 CX / 11 wires**, its 13/3/0 collision counts, and quantum compute/phase/inverse
correctness on all 64 y inputs (error 2.86e-15). The original source's `check`
was classical; this audit additionally checks the compiled native circuit.

## Corrections to the interpretation

- 29..53 inclusive is **25**, not 35, values. It crosses a binary block boundary,
  but length greater than 32 is not the reason. Under band `[y>=28]`, low-five
  inputs 28..31 collide modulo 32 with 60..63 while sharing the same band.
- Raw magnitude occupies four bits. `(band,mag)`, `(band,sign,mag)` and
  `(band,sign,mag,y5)` occupy **5, 6 and 7 bits**, respectively. A hypothetical
  bucketed representation needs a separate explicit definition and check.
- Two odd centres cannot become complementary under a common integer shift:
  this excludes that specific all-low-bits one's-complement alignment. It does
  not exclude other arithmetic representations, comparisons in original
  coordinates, or piecewise transformations. An odd addend does not prove a
  mandatory native-depth carry schedule or a requirement for a primitive
  four-control gate.
- A previously measured ten-wire phase kernel's 711 terms/382 layers is not a
  lower bound for other ten-wire functions, and no such kernel was built here.
- A disk-only phase component need not retain enough information to classify
  the rectangles. The complete oracle must still apply their phases correctly,
  including overlaps; deleting that requirement globally would be incorrect.

## Measured alternative band

The disks have y-support 11..27 and 35..47. Therefore y5 already selects the
relevant disk. Replacing the computed `[y>=28]` flag with y5 gives the same
per-band modular centring operation for those disk domains:

| Fold | Depth | CX | Wires |
| --- | ---: | ---: | ---: |
| Original full-row band | 95 | 71 | 11 |
| Disk-only y5 band | **74** | **56** | **9** |

The latter uses three helpers. All 64 basis mappings and helper restoration
are checked, as is native compute/Z/inverse (error 2.91e-15). Interpreting the
folded absolute distance in the selected disk's inequality matches the union
of the two original disks on **all 4096 x/y pairs**, including outside their
supports. This is not a full-logo descriptor or a complete quantum disk oracle.

Artifacts: `artifacts/post190_y_fold_audit/{original,disk_y5}.qasm` and
`report.json`. Neither is a submission. Merely computing and uncomputing the
74-layer fold is still unattractive; this audit does not defend that integration.

A separate bounded signed-power-addition probe considered 18 decompositions
of +13 and 26 controlled decompositions of +10 (at most three signed powers of
two), and all 468 paired schedules. Best combined disk fold remained 74/56.
This is a restricted schedule search, not an optimality certificate.

## Concrete alternative without a y fold

Derive a **vertical radius from folded x**, then test the original y coordinate
against the two bounds around centre 19 or 41. Constant offsets belong inside
the comparisons; do not first materialize a centred y register. The x-fold's
band is already y5. The x high-bit condition and all rectangle phases remain
part of the complete construction's contract.

Exact radii from horizontal distance d are:

- R-squared 72, d=0..8: `[8,8,8,7,7,6,6,4,2]`.
- R-squared 42, d=0..6: `[6,6,6,5,5,4,2]`.

The nonempty radii are `{2,4,5,6,7,8}`. Encoding **t=r-1** gives
`{1,3,4,5,6,7}` in three bits, with **0 reserved for empty**. Thus the radius-8
exception and empty/zero-radius collision are not inevitable for this disk-only
contract. Check `t != 0` as well as `c-(t+1) <= y <= c+(t+1)`.

This is an exact encoding observation, not a depth result. The radius loader
still depends on the folded x sign/magnitude and disk selection; its cost is
unmeasured. So are the fused bound comparisons, workspace scheduling and full
rectangle/overlap integration. These must be measured before recommending a
submission or claiming a route to 136. No background jobs remain.
