// Enumerate all 4-dim subspaces S (code row spaces) of GF(2)^9 such that the code separates classes.
// Input: side char, then 9 hex truth tables on stdin. Output: one line per separating subspace: 4 masks (RREF).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "classes.h"
int main(int argc, char **argv) {
  const int *CLS = argv[1][0] == 'x' ? COLCLS : ROWCLS;
  uint64_t w[9]; for (int k = 0; k < 9; k++) { if (scanf("%llx", (unsigned long long *)&w[k]) != 1) return 1; }
  int vec[64]; for (int x = 0; x < 64; x++) { int v = 0; for (int k = 0; k < 9; k++) v |= (int)((w[k] >> x) & 1) << k; vec[x] = v; }
  static int bad[512]; memset(bad, 0, sizeof bad);
  for (int a = 0; a < 64; a++) for (int b = a + 1; b < 64; b++) if (CLS[a] != CLS[b]) bad[vec[a] ^ vec[b]] = 1;
  // code with rowspace S separates iff no bad v has g.v = 0 for all g in S  <=> bad v not in S^perp.
  // Enumerate RREF 4x9 matrices: pivots p0<p1<p2<p3, free entries to the right of pivot not in pivot columns.
  long count = 0, sep = 0;
  for (int p0 = 0; p0 < 9; p0++) for (int p1 = p0 + 1; p1 < 9; p1++) for (int p2 = p1 + 1; p2 < 9; p2++) for (int p3 = p2 + 1; p3 < 9; p3++) {
    int piv[4] = {p0, p1, p2, p3}; int pivmask = (1 << p0) | (1 << p1) | (1 << p2) | (1 << p3);
    int freecols[4][9]; int nf[4];
    for (int r = 0; r < 4; r++) { nf[r] = 0; for (int j = piv[r] + 1; j < 9; j++) if (!((pivmask >> j) & 1)) freecols[r][nf[r]++] = j; }
    int tot = nf[0] + nf[1] + nf[2] + nf[3];
    for (long m = 0; m < (1L << tot); m++) {
      int rows[4]; long mm = m;
      for (int r = 0; r < 4; r++) { rows[r] = 1 << piv[r]; for (int f = 0; f < nf[r]; f++) { if (mm & 1) rows[r] |= 1 << freecols[r][f]; mm >>= 1; } }
      count++;
      int ok = 1;
      for (int v = 1; v < 512 && ok; v++) if (bad[v]) {
        int z = 1; for (int r = 0; r < 4; r++) if (__builtin_popcount(rows[r] & v) & 1) { z = 0; break; }
        if (z) ok = 0;
      }
      if (ok) { sep++; printf("%d %d %d %d\n", rows[0], rows[1], rows[2], rows[3]); }
    }
  }
  fprintf(stderr, "subspaces %ld separating %ld\n", count, sep);
  return 0;
}
