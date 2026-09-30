// Physical-template annealer with multiplicity-aware 4-bit code objective.
// stage = L CX layers + <=3 disjoint Toffolis (with control negations).
// score = A*collisions + B*extra, where extra = sum over classes (#distinct codes - 1).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "classes.h"
#define W 9
#define MAXT 10
#define MAXL 4
typedef uint64_t u64;
static int T, L; static const int *CLS; static double WA = 10, WB = 3;
typedef struct { int8_t ctl[W]; } CxLayer;
typedef struct { int8_t c1, c2, t; uint8_t n1, n2, en; } Tof;
typedef struct { CxLayer cx[MAXT][MAXL]; Tof tof[MAXT][3]; } Circ;
static u64 rs[2];
static inline u64 rotl(u64 x, int k) { return (x << k) | (x >> (64 - k)); }
static inline u64 rnd(void) { u64 s0 = rs[0], s1 = rs[1], r = s0 + s1; s1 ^= s0; rs[0] = rotl(s0, 55) ^ s1 ^ (s1 << 14); rs[1] = rotl(s1, 36); return r; }
static inline int rndi(int n) { return (int)(rnd() % (u64)n); }
static inline double rndf(void) { return (rnd() >> 11) * (1.0 / 9007199254740992.0); }
static int nbad, nsame; static int PMASK; static u64 PTT; static uint8_t ba[2100], bb[2100], sa_[2100], sb[2100];
static void simulate(const Circ *c, u64 w[W]) {
  for (int k = 0; k < W; k++) { w[k] = 0; if (k < 6) for (int x = 0; x < 64; x++) if ((x >> k) & 1) w[k] |= 1ULL << x; }
  for (int t = 0; t < T; t++) {
    for (int l = 0; l < L; l++) { u64 nw[W]; memcpy(nw, w, sizeof nw);
      for (int k = 0; k < W; k++) if (c->cx[t][l].ctl[k] >= 0) nw[k] ^= w[c->cx[t][l].ctl[k]]; memcpy(w, nw, sizeof nw); }
    u64 nw[W]; memcpy(nw, w, sizeof nw);
    for (int i = 0; i < 3; i++) { const Tof *f = &c->tof[t][i]; if (!f->en) continue;
      nw[f->t] ^= (w[f->c1] ^ (f->n1 ? ~0ULL : 0)) & (w[f->c2] ^ (f->n2 ? ~0ULL : 0)); }
    memcpy(w, nw, sizeof nw);
  }
}
static double wh[512];
static int in_span(const u64 w[W], u64 target, int *mask_out) {
  // Gaussian elimination over truth tables; returns 1 if target in span, with combination mask
  u64 rows[W]; int comb[W]; int n = 0;
  for (int k = 0; k < W; k++) { u64 r = w[k]; int cm = 1 << k;
    for (int i = 0; i < n; i++) { int pb = __builtin_ctzll(rows[i]); if ((r >> pb) & 1) { r ^= rows[i]; cm ^= comb[i]; } }
    if (r) { rows[n] = r; comb[n] = cm; n++; } }
  u64 t = target; int cm = 0;
  for (int i = 0; i < n; i++) { int pb = __builtin_ctzll(rows[i]); if ((t >> pb) & 1) { t ^= rows[i]; cm ^= comb[i]; } }
  // also allow complement (affine)
  if (t == 0) { if (mask_out) *mask_out = cm; return 1; }
  t = ~target; cm = 0;
  for (int i = 0; i < n; i++) { int pb = __builtin_ctzll(rows[i]); if ((t >> pb) & 1) { t ^= rows[i]; cm ^= comb[i]; } }
  if (t == 0) { if (mask_out) *mask_out = cm; return 1; }
  return 0;
}
static double eval_code(const u64 w[W], int G[4], int reps, int *col_out, int *extra_out) {
  int vec[64]; for (int x = 0; x < 64; x++) { int v = 0; for (int k = 0; k < W; k++) v |= (int)((w[k] >> x) & 1) << k; vec[x] = v; }
  int pm = 0; int have_p = in_span(w, PTT, &pm);
  static double cnt[512]; for (int i = 0; i < 512; i++) cnt[i] = 0;
  for (int p = 0; p < nbad; p++) cnt[vec[ba[p]] ^ vec[bb[p]]] += WA;
  for (int p = 0; p < nsame; p++) cnt[vec[sa_[p]] ^ vec[sb[p]]] -= 0.25 * WB;
  for (int i = 0; i < 512; i++) wh[i] = cnt[i];
  for (int h = 1; h < 512; h <<= 1) for (int i = 0; i < 512; i += 2 * h) for (int j = i; j < i + h; j++) { double a = wh[j], b = wh[j + h]; wh[j] = a + b; wh[j + h] = a - b; }
  double best = 1e30; int bestG[3] = {0};
  for (int rep = 0; rep < reps; rep++) {
    int S[8]; int ns = 1; S[0] = 0; int gsel[3]; double sum = wh[0];
    for (int d = 0; d < 3; d++) { double bestadd = 1e30; int cand[512]; int nc = 0;
      for (int g = 1; g < 512; g++) { int inS = 0; for (int s = 0; s < ns; s++) if (S[s] == g) { inS = 1; break; } if (inS) continue;
        double add = 0; for (int s = 0; s < ns; s++) add += wh[S[s] ^ g];
        if (add < bestadd - 1e-9) { bestadd = add; nc = 0; cand[nc++] = g; } else if (fabs(add - bestadd) < 1e-9) cand[nc++] = g; }
      int bg = rep == 0 ? cand[0] : cand[rndi(nc)]; gsel[d] = bg; sum += bestadd; for (int s = 0; s < ns; s++) S[ns + s] = S[s] ^ bg; ns *= 2; }
    int improved = 1;
    while (improved) { improved = 0;
      for (int d = 0; d < 3 && !improved; d++) { int R[4]; int nr = 1; R[0] = 0;
        for (int e = 0; e < 3; e++) if (e != d) { for (int s = 0; s < nr; s++) R[nr + s] = R[s] ^ gsel[e]; nr *= 2; }
        double base = 0; for (int s = 0; s < nr; s++) base += wh[R[s]]; double cur = sum - base;
        for (int g = 1; g < 512; g++) { int inR = 0; for (int s = 0; s < nr; s++) if (R[s] == g) { inR = 1; break; } if (inR) continue;
          double add = 0; for (int s = 0; s < nr; s++) add += wh[R[s] ^ g]; if (add < cur - 1e-9) { gsel[d] = g; sum = base + add; improved = 1; break; } } } }
    if (sum < best) { best = sum; memcpy(bestG, gsel, sizeof bestG); }
  }
  int lab[64]; for (int x = 0; x < 64; x++) { int c = 0; for (int d = 0; d < 3; d++) c |= (__builtin_popcount(bestG[d] & vec[x]) & 1) << d; lab[x] = c; }
  int col = 0; for (int p = 0; p < nbad; p++) if (lab[ba[p]] == lab[bb[p]]) col++;
  int used[2][11]; memset(used, 0, sizeof used);
  for (int x = 0; x < 64; x++) used[__builtin_popcount(x & PMASK) & 1][CLS[x]] |= 1 << lab[x];
  int extra = 0; for (int h = 0; h < 2; h++) for (int k = 0; k < 11; k++) if (used[h][k]) extra += __builtin_popcount(used[h][k]) - 1;
  if (G) { G[0] = have_p ? pm : -1; G[1] = bestG[0]; G[2] = bestG[1]; G[3] = bestG[2]; }
  if (col_out) *col_out = col; if (extra_out) *extra_out = extra;
  return WA * col + WB * extra + (have_p ? 0 : 1000);
}
static int used_in_batch(const Circ *c, int t, int skip, int wire) { for (int i = 0; i < 3; i++) { if (i == skip) continue; const Tof *f = &c->tof[t][i]; if (!f->en) continue; if (f->c1 == wire || f->c2 == wire || f->t == wire) return 1; } return 0; }
static void random_tof(Tof *f) { int a[W]; for (int i = 0; i < W; i++) a[i] = i; for (int i = 0; i < 3; i++) { int j = i + rndi(W - i); int tmp = a[i]; a[i] = a[j]; a[j] = tmp; } f->c1 = a[0]; f->c2 = a[1]; f->t = a[2]; f->n1 = rndi(2); f->n2 = rndi(2); f->en = 1; }
static void mutate(Circ *c) {
  int kind = rndi(10); int t = rndi(T);
  if (kind < 5 && L > 0) { CxLayer *ly = &c->cx[t][rndi(L)]; int op = rndi(3);
    if (op == 0) ly->ctl[rndi(W)] = -1;
    else { int a = rndi(W), b = rndi(W); if (a == b) return; for (int k = 0; k < W; k++) if (ly->ctl[k] == a || ly->ctl[k] == b) ly->ctl[k] = -1; ly->ctl[a] = -1; ly->ctl[b] = a; }
  } else { int i = rndi(3); Tof *f = &c->tof[t][i]; int op = rndi(5);
    if (op == 0) { f->en = !f->en; if (f->en) { for (int tries = 0; tries < 50; tries++) { random_tof(f); if (!used_in_batch(c, t, i, f->c1) && !used_in_batch(c, t, i, f->c2) && !used_in_batch(c, t, i, f->t)) return; } f->en = 0; } }
    else if (op == 1) f->n1 ^= 1; else if (op == 2) f->n2 ^= 1;
    else { if (!f->en) return; int which = rndi(3); int nw = rndi(W); if (used_in_batch(c, t, i, nw)) return;
      if (which == 0 && nw != f->c2 && nw != f->t) f->c1 = nw; else if (which == 1 && nw != f->c1 && nw != f->t) f->c2 = nw; else if (which == 2 && nw != f->c1 && nw != f->c2) f->t = nw; } }
}
int main(int argc, char **argv) {
  if (argc < 9) { fprintf(stderr, "usage: side T L secs seed temp0 WA WB\n"); return 1; }
  CLS = argv[1][0] == 'x' ? COLCLS : ROWCLS; T = atoi(argv[2]); L = atoi(argv[3]); double secs = atof(argv[4]); u64 seed = strtoull(argv[5], 0, 10); double temp0 = atof(argv[6]); WA = atof(argv[7]); WB = atof(argv[8]);
  rs[0] = seed * 0x9E3779B97F4A7C15ULL + 3; rs[1] = seed ^ 0xD1B54A32D192ED03ULL; for (int i = 0; i < 20; i++) rnd();
  PMASK = argv[1][0] == 'x' ? 48 : 32; PTT = 0; for (int x = 0; x < 64; x++) if (__builtin_popcount(x & PMASK) & 1) PTT |= 1ULL << x;
  for (int a = 0; a < 64; a++) for (int b = a + 1; b < 64; b++) { if ((__builtin_popcount(a & PMASK) ^ __builtin_popcount(b & PMASK)) & 1) continue; if (CLS[a] != CLS[b]) { ba[nbad] = a; bb[nbad] = b; nbad++; } else { sa_[nsame] = a; sb[nsame] = b; nsame++; } }
  Circ cur; memset(&cur, 0, sizeof cur);
  for (int t = 0; t < T; t++) for (int l = 0; l < L; l++) for (int k = 0; k < W; k++) cur.cx[t][l].ctl[k] = -1;
  u64 w[W]; int G[4]; int col, extra; simulate(&cur, w);
  double cc = eval_code(w, G, 3, &col, &extra); double bestc = cc; Circ best = cur;
  clock_t start = clock(); long it = 0;
  while (1) {
    double el = (double)(clock() - start) / CLOCKS_PER_SEC; if ((it & 1023) == 0 && el > secs) break;
    double temp = temp0 * pow(0.001, el / secs) + 0.05;
    Circ nxt = cur; int nm = 1 + rndi(2); for (int m = 0; m < nm; m++) mutate(&nxt);
    simulate(&nxt, w); double nc = eval_code(w, 0, 2, &col, &extra);
    if (nc <= cc || rndf() < exp((cc - nc) / temp)) { cur = nxt; cc = nc;
      if (cc < bestc) { bestc = cc; best = cur; fprintf(stderr, "it %ld t=%.1fs score %.1f col %d extra %d\n", it, el, cc, col, extra); } }
    it++;
  }
  simulate(&best, w); double sc = eval_code(w, G, 30, &col, &extra);
  printf("{\"T\":%d,\"L\":%d,\"score\":%.1f,\"col\":%d,\"extra\":%d,\"stages\":[", T, L, sc, col, extra);
  for (int t = 0; t < T; t++) { printf("%s{\"cx\":[", t ? "," : "");
    for (int l = 0; l < L; l++) { printf("%s[", l ? "," : ""); int first = 1; for (int k = 0; k < W; k++) if (best.cx[t][l].ctl[k] >= 0) { printf("%s[%d,%d]", first ? "" : ",", best.cx[t][l].ctl[k], k); first = 0; } printf("]"); }
    printf("],\"tof\":["); int first = 1; for (int i = 0; i < 3; i++) { const Tof *f = &best.tof[t][i]; if (!f->en) continue; printf("%s[%d,%d,%d,%d,%d]", first ? "" : ",", f->c1, f->c2, f->t, f->n1, f->n2); first = 0; } printf("]}"); }
  printf("],\"G\":[%d,%d,%d,%d]}\n", G[0], G[1], G[2], G[3]);
  fprintf(stderr, "done it=%ld score=%.1f col=%d extra=%d\n", it, sc, col, extra);
  return 0;
}
