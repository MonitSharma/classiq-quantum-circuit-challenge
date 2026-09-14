# The geometry/arithmetic oracle, costed end to end

Protected best unchanged: **190 depth / 857 CX / 18 qubits**, `artifacts/190/`.

This is the complete arithmetic construction with a real resource schedule, not
an estimate. Every row below is a compiled u3/cx measurement, and the assembled
oracle is exhaustively verified on all 4096 basis inputs.

## The decomposition

Verified exactly on all 4096 coordinates (`post190_radius_interval.build`):

    logo(x,y) = disk(x,y) XOR rect(x,y),  the two never both true

    disk = x5 and t != 0 and  c - t - 1 <= (y mod 32) <= c + t + 1
           where c = 19 if y5 = 0 else 9,
           and t = radius lookup of the folded x together with y5
    rect = [2 <= x <= 26][29 <= y <= 53]  or  [27 <= x <= 48][39 <= y <= 43]

Overlaps are handled by construction, not by XOR-ing the original shapes: the
disk's y window is cut to the band that the rectangles do not occupy, and the
disjointness is asserted for every (x,y) pair before the circuit is built.

## Schedule

| stage | depth | CX |
|---|---:|---:|
| x fold (`x ^= 31` on y5, `-8`, one's-complement) | 10 | 10 |
| radius lookup, 6 address bits -> 3 radius bits | 77 | 173 |
| **encoder E = fold + lookup** | **85** | **183** |
| interval phase (one modular ripple + 4 majorities) | 500 | 363 |
| encoder inverse | 85 | 183 |
| disk block `E K E†` after merging | 668 | — |
| rectangle phase (prefix-cube bounds) | 835 | 527 |
| **whole oracle, exhaustively verified** | **1498** | **1252** |

`artifacts/post190_rect_prefix/oracle.qasm`, sha256
`0336a991a8f8a3733bd5a9534c9f4f99afa4688f3c84ad5c336aa17ed00948fa`,
4096 inputs at 1.73e-14, ancilla error 2.12e-15, width 18.

## What the two rebuilds bought

| build | interval | rectangles | oracle |
|---|---:|---:|---:|
| dyadic cube cover | 875 | 1487 | 2524 |
| threshold register via MCX ladders | 1649 | 1487 | 3303 |
| **ripple window + prefix cubes** | **500** | **835** | **1498** |

The threshold-register version was the slowest because it materialises `c +/- t`
in a five-bit register while all six ancillas are already committed, so every
constant addition needs ancilla-free multi-controlled gates.

The replacement never forms a threshold at all. Writing the window test as

    r = (v + t + K) mod 32,  K = (1-c) mod 32 = 8 + 6(1-y5) + 16 y5
    window  <=>  r <= 2t+2  <=>  not ( r >= 2(t+1)+1 )

makes the only register ever built `t+1`, on the radius wires themselves, and the
comparison four majority gates: the `~B+1` addend has bit 0 equal to 0 against a
carry-in of 1, so the first carry is just `r0` and costs nothing. The band
difference between the two disk centres survives as a per-bit literal in y5
(`K` bits are `0, ~y5, ~y5, 1, y5`), so one block serves both bands. The block is
checked on all 1024 (v, t, y5, x5) assignments.

The rectangle bounds use disjoint prefix cubes: `[v < k]` is one cube per one bit
of k, `[v >= k] = [v > k-1]` is one cube per zero bit of `k-1`, and the shorter
list is taken (checked for every threshold 1..64). That is 20 cubes for the eight
bounds where the dyadic cover needed 38.

## Why the route still loses, and by how much

The encoder is not shared: it appears once to load the radius and once to unload
it. That is **2 x 85 = 170 layers before any phase work at all**, which is

* already above the 136 needed to take the top of the leaderboard, and
* only 20 below the entire protected 190-depth oracle.

The two phase blocks that must fit inside that 20 layers measure 500 and 835.

The sharpest way to see the gap: the rectangle phase alone computes a strictly
easier function than the logo -- two axis-aligned boxes, no disks -- and costs
835, which is 4.4x the cost of the whole logo in the class-code architecture.
Geometric structure that is obvious to a human is not what makes a phase oracle
shallow; what makes it shallow is loading a short code once per coordinate and
paying for the interaction in a narrow kernel.

## Status

The arithmetic route is now costed rather than argued about, at 1498 verified.
Three independent implementations of the same decomposition span 3303 to 1498,
so implementation quality moves it by more than a factor of two -- and the floor
it is converging on, 170 for the encoder pair, is still above the target. Sub-140
will not come from this decomposition.

See also [POST190_Y_FOLD_COST.md](POST190_Y_FOLD_COST.md) for the y-side fold,
which was the other half of this plan and costs 95 against the 77 it replaces.
