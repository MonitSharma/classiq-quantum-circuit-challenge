// Simulated annealing for 9-wire reversible class encoders.
// Template: T stages; each stage = L CX layers, then one Toffoli batch (<=3 disjoint Toffolis).
// Objective: min over 4-bit linear codes of #class-colliding pairs (0 = separating code).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "classes.h"
#define W 9
#define MAXT 8
#define MAXL 4
typedef uint64_t u64;
static int T, L, NCODE = 4;
static const int *CLS;
typedef struct { int8_t ctl[W]; } CxLayer;        // ctl[t] = control wire for target t, or -1
typedef struct { int8_t c1, c2, t; uint8_t n1, n2, en; } Tof;
typedef struct { CxLayer cx[MAXT][MAXL]; Tof tof[MAXT][3]; } Circ;
static u64 rng_s[2];
static inline u64 rotl(const u64 x, int k) { return (x << k) | (x >> (64 - k)); }
static inline u64 rnd(void) { u64 s0 = rng_s[0], s1 = rng_s[1], r = s0 + s1; s1 ^= s0; rng_s[0] = rotl(s0, 55) ^ s1 ^ (s1 << 14); rng_s[1] = rotl(s1, 36); return r; }
static inline int rndi(int n) { return (int)(rnd() % (u64)n); }
static inline double rndf(void) { return (rnd() >> 11) * (1.0 / 9007199254740992.0); }
static int npairs; static uint8_t pa[2100], pb[2100];

static void simulate(const Circ *c, u64 w[W]) {
  for (int k = 0; k < W; k++) { w[k] = 0; if (k < 6) for (int x = 0; x < 64; x++) if ((x >> k) & 1) w[k] |= 1ULL << x; }
  for (int t = 0; t < T; t++) {
    for (int l = 0; l < L; l++) {
      u64 nw[W]; memcpy(nw, w, sizeof(nw));
      for (int k = 0; k < W; k++) if (c->cx[t][l].ctl[k] >= 0) nw[k] ^= w[c->cx[t][l].ctl[k]];
      memcpy(w, nw, sizeof(nw));
    }
    u64 nw[W]; memcpy(nw, w, sizeof(nw));
    for (int i = 0; i < 3; i++) { const Tof *f = &c->tof[t][i]; if (!f->en) continue;
      u64 a = w[f->c1] ^ (f->n1 ? ~0ULL : 0), b = w[f->c2] ^ (f->n2 ? ~0ULL : 0); nw[f->t] ^= a & b; }
    memcpy(w, nw, sizeof(nw));
  }
}
// collisions via Walsh of difference counts
static int wh[512];
static long best_code(const u64 w[W], int G[4]) {
  int vec[64]; for (int x = 0; x < 64; x++) { int v = 0; for (int k = 0; k < W; k++) v |= (int)((w[k] >> x) & 1) << k; vec[x] = v; }
  static int cnt[512]; memset(cnt, 0, sizeof(cnt));
  for (int p = 0; p < npairs; p++) cnt[vec[pa[p]] ^ vec[pb[p]]]++;
  // injectivity check: identical vectors for different x => impossible (reversible) so ignore
  for (int i = 0; i < 512; i++) wh[i] = cnt[i];
  for (int h = 1; h < 512; h <<= 1) for (int i = 0; i < 512; i += 2 * h) for (int j = i; j < i + h; j++) { int a = wh[j], b = wh[j + h]; wh[j] = a + b; wh[j + h] = a - b; }
  // greedy build 4-dim subspace S minimizing sum_{g in S} wh[g]; collisions = sum/16
  int best_total = 1 << 30; int bestG[8] = {0};
  for (int rep = 0; rep < 3; rep++) {
    int S[64]; int ns = 1; S[0] = 0; int gsel[8]; long sum = wh[0];
    for (int d = 0; d < NCODE; d++) {
      long bestadd = 1L << 40; int bestg = -1; int cand[512]; int nc = 0;
      for (int g = 1; g < 512; g++) {
        int inS = 0; for (int s = 0; s < ns; s++) if (S[s] == g) { inS = 1; break; }
        if (inS) continue;
        long add = 0; for (int s = 0; s < ns; s++) add += wh[S[s] ^ g];
        if (add < bestadd) { bestadd = add; bestg = g; nc = 0; cand[nc++] = g; }
        else if (add == bestadd && nc < 512) cand[nc++] = g;
      }
      if (rep > 0 && nc > 1) bestg = cand[rndi(nc)];
      gsel[d] = bestg; sum += bestadd;
      for (int s = 0; s < ns; s++) S[ns + s] = S[s] ^ bestg; ns *= 2;
    }
    // local improvement: try replacing one generator
    int improved = 1;
    while (improved) { improved = 0;
      for (int d = 0; d < NCODE && !improved; d++) {
        // subspace spanned by other generators
        int R[64]; int nr = 1; R[0] = 0;
        for (int e = 0; e < NCODE; e++) if (e != d) { for (int s = 0; s < nr; s++) R[nr + s] = R[s] ^ gsel[e]; nr *= 2; }
        long base = 0; for (int s = 0; s < nr; s++) base += wh[R[s]];
        long cur = sum - base;
        for (int g = 1; g < 512; g++) { int inR = 0; for (int s = 0; s < nr; s++) if (R[s] == g) { inR = 1; break; } if (inR) continue;
          long add = 0; for (int s = 0; s < nr; s++) add += wh[R[s] ^ g];
          if (add < cur) { gsel[d] = g; sum = base + add; improved = 1; break; } }
      }
    }
    int total = (int)(sum / (1 << NCODE));
    if (total < best_total) { best_total = total; memcpy(bestG, gsel, sizeof(bestG)); }
    if (best_total == 0) break;
  }
  if (G) memcpy(G, bestG, sizeof(bestG));
  return best_total;
}
static void random_tof(Tof *f) { int w3[W]; for (int i = 0; i < W; i++) w3[i] = i; for (int i = 0; i < 3; i++) { int j = i + rndi(W - i); int tmp = w3[i]; w3[i] = w3[j]; w3[j] = tmp; }
  f->c1 = w3[0]; f->c2 = w3[1]; f->t = w3[2]; f->n1 = rndi(2); f->n2 = rndi(2); f->en = 1; }
static int used_in_batch(const Circ *c, int t, int skip, int wire) { for (int i = 0; i < 3; i++) { if (i == skip) continue; const Tof *f = &c->tof[t][i]; if (!f->en) continue; if (f->c1 == wire || f->c2 == wire || f->t == wire) return 1; } return 0; }
static int layer_busy(const CxLayer *ly, int wire) { if (ly->ctl[wire] >= 0) return 1; for (int k = 0; k < W; k++) if (ly->ctl[k] == wire) return 1; return 0; }
static void mutate(Circ *c) {
  int kind = rndi(10); int t = rndi(T);
  if (kind < 5 && L > 0) { // CX edit
    CxLayer *ly = &c->cx[t][rndi(L)];
    int op = rndi(3);
    if (op == 0) { int k = rndi(W); ly->ctl[k] = -1; }
    else { int a = rndi(W), b = rndi(W); if (a == b) return;
      // clear any gates on a,b then set b <- a
      for (int k = 0; k < W; k++) { if (ly->ctl[k] == a || ly->ctl[k] == b) ly->ctl[k] = -1; }
      ly->ctl[a] = -1; ly->ctl[b] = a; }
  } else { // Toffoli edit
    int i = rndi(3); Tof *f = &c->tof[t][i]; int op = rndi(5);
    if (op == 0) { f->en = !f->en; if (f->en) { for (int tries = 0; tries < 50; tries++) { random_tof(f); if (!used_in_batch(c, t, i, f->c1) && !used_in_batch(c, t, i, f->c2) && !used_in_batch(c, t, i, f->t)) return; } f->en = 0; } }
    else if (op == 1) { f->n1 ^= 1; } else if (op == 2) { f->n2 ^= 1; }
    else { if (!f->en) return; int which = rndi(3); int nwire = rndi(W); if (used_in_batch(c, t, i, nwire)) return;
      if (which == 0 && nwire != f->c2 && nwire != f->t) f->c1 = nwire; else if (which == 1 && nwire != f->c1 && nwire != f->t) f->c2 = nwire; else if (which == 2 && nwire != f->c1 && nwire != f->c2) f->t = nwire; }
  }
}
static void print_circ(const Circ *c, const u64 w[W], int G[8], long cost) {
  printf("{\"T\":%d,\"L\":%d,\"cost\":%ld,\"stages\":[", T, L, cost);
  for (int t = 0; t < T; t++) { printf("%s{\"cx\":[", t ? "," : "");
    for (int l = 0; l < L; l++) { printf("%s[", l ? "," : ""); int first = 1; for (int k = 0; k < W; k++) if (c->cx[t][l].ctl[k] >= 0) { printf("%s[%d,%d]", first ? "" : ",", c->cx[t][l].ctl[k], k); first = 0; } printf("]"); }
    printf("],\"tof\":["); int first = 1; for (int i = 0; i < 3; i++) { const Tof *f = &c->tof[t][i]; if (!f->en) continue; printf("%s[%d,%d,%d,%d,%d]", first ? "" : ",", f->c1, f->c2, f->t, f->n1, f->n2); first = 0; }
    printf("]}"); }
  printf("],\"G\":["); for (int d = 0; d < NCODE; d++) printf("%s%d", d ? "," : "", G[d]); printf("]}\n"); fflush(stdout);
}
int main(int argc, char **argv) {
  if (argc < 6) { fprintf(stderr, "usage: anneal side T L seconds seed\n"); return 1; }
  CLS = argv[1][0] == 'x' ? COLCLS : ROWCLS; T = atoi(argv[2]); L = atoi(argv[3]); double secs = atof(argv[4]); u64 seed = strtoull(argv[5], 0, 10);
  rng_s[0] = seed * 0x9E3779B97F4A7C15ULL + 1; rng_s[1] = seed ^ 0xD1B54A32D192ED03ULL; for (int i = 0; i < 20; i++) rnd();
  npairs = 0; for (int a = 0; a < 64; a++) for (int b = a + 1; b < 64; b++) if (CLS[a] != CLS[b]) { pa[npairs] = a; pb[npairs] = b; npairs++; }
  Circ cur; memset(&cur, 0, sizeof(cur));
  for (int t = 0; t < T; t++) { for (int l = 0; l < L; l++) for (int k = 0; k < W; k++) cur.cx[t][l].ctl[k] = -1;
    for (int i = 0; i < 3; i++) cur.tof[t][i].en = 0; }
  u64 w[W]; int G[8]; simulate(&cur, w); long cc = best_code(w, G); long bestc = cc; Circ best = cur;
  clock_t start = clock(); long it = 0; double temp0 = argc > 6 ? atof(argv[6]) : 30.0; NCODE = argc > 7 ? atoi(argv[7]) : 4;
  while (1) {
    if ((it & 255) == 0) { double el = (double)(clock() - start) / CLOCKS_PER_SEC; if (el > secs) break; }
    double el = (double)(clock() - start) / CLOCKS_PER_SEC; double temp = temp0 * pow(0.002, el / secs) + 0.05;
    Circ nxt = cur; int nm = 1 + rndi(2); for (int m = 0; m < nm; m++) mutate(&nxt);
    simulate(&nxt, w); long nc = best_code(w, 0);
    if (nc <= cc || rndf() < exp((cc - nc) / temp)) { cur = nxt; cc = nc; if (cc < bestc) { bestc = cc; best = cur; fprintf(stderr, "it %ld t=%.1fs cost %ld\n", it, el, bestc); if (bestc == 0) break; } }
    it++;
  }
  simulate(&best, w); best_code(w, G); print_circ(&best, w, G, bestc);
  fprintf(stderr, "done it=%ld best=%ld\n", it, bestc);
  return 0;
}
