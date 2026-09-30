// Abstract-stage annealer: stage = <=3 Toffolis (alpha,beta,lambda in GF(2)^9), alpha.lambda=beta.lambda=0,
// rank conditions. Objective: collisions of best 4-bit code (+ tiny weight penalty).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "classes.h"
#define W 9
#define MAXT 8
static int NC = 4;
typedef uint64_t u64;
static int T; static const int *CLS; static int npairs; static uint8_t pa[2100], pb[2100];
typedef struct { uint16_t a, b, l; uint8_t en; } Tof;
typedef struct { Tof t[MAXT][3]; } Circ;
static u64 rs[2];
static inline u64 rotl(u64 x, int k) { return (x << k) | (x >> (64 - k)); }
static inline u64 rnd(void) { u64 s0 = rs[0], s1 = rs[1], r = s0 + s1; s1 ^= s0; rs[0] = rotl(s0, 55) ^ s1 ^ (s1 << 14); rs[1] = rotl(s1, 36); return r; }
static inline int rndi(int n) { return (int)(rnd() % (u64)n); }
static inline double rndf(void) { return (rnd() >> 11) * (1.0 / 9007199254740992.0); }
static int rank_of(int *v, int n) { int r = 0; int m[16]; memcpy(m, v, n * sizeof(int));
  for (int bit = 0; bit < W; bit++) { int p = -1; for (int i = r; i < n; i++) if ((m[i] >> bit) & 1) { p = i; break; } if (p < 0) continue;
    int tmp = m[r]; m[r] = m[p]; m[p] = tmp; for (int i = 0; i < n; i++) if (i != r && ((m[i] >> bit) & 1)) m[i] ^= m[r]; r++; } return r; }
static int valid_stage(const Tof *s) {
  int ab[6], ls[3], k = 0;
  for (int i = 0; i < 3; i++) if (s[i].en) { ab[2 * k] = s[i].a; ab[2 * k + 1] = s[i].b; ls[k] = s[i].l; k++; }
  if (k == 0) return 1;
  for (int i = 0; i < 2 * k; i++) for (int j = 0; j < k; j++) if (__builtin_popcount(ab[i] & ls[j]) & 1) return 0;
  if (rank_of(ab, 2 * k) != 2 * k) return 0;
  if (rank_of(ls, k) != k) return 0;
  return 1;
}
static void simulate(const Circ *c, u64 w[W]) {
  for (int k = 0; k < W; k++) { w[k] = 0; if (k < 6) for (int x = 0; x < 64; x++) if ((x >> k) & 1) w[k] |= 1ULL << x; }
  for (int t = 0; t < T; t++) {
    u64 p[3]; int en[3];
    for (int i = 0; i < 3; i++) { const Tof *f = &c->t[t][i]; en[i] = f->en; if (!f->en) continue;
      u64 a = 0, b = 0; for (int j = 0; j < W; j++) { if ((f->a >> j) & 1) a ^= w[j]; if ((f->b >> j) & 1) b ^= w[j]; } p[i] = a & b; }
    for (int i = 0; i < 3; i++) if (en[i]) { const Tof *f = &c->t[t][i]; for (int j = 0; j < W; j++) if ((f->l >> j) & 1) w[j] ^= p[i]; }
  }
}
static int wh[512];
static long best_code(const u64 w[W], int G[4], int reps) {
  int vec[64]; for (int x = 0; x < 64; x++) { int v = 0; for (int k = 0; k < W; k++) v |= (int)((w[k] >> x) & 1) << k; vec[x] = v; }
  static int cnt[512]; memset(cnt, 0, sizeof(cnt));
  for (int p = 0; p < npairs; p++) cnt[vec[pa[p]] ^ vec[pb[p]]]++;
  if (cnt[0]) return 100000; // non-injective on differing classes (should not happen)
  for (int i = 0; i < 512; i++) wh[i] = cnt[i];
  for (int h = 1; h < 512; h <<= 1) for (int i = 0; i < 512; i += 2 * h) for (int j = i; j < i + h; j++) { int a = wh[j], b = wh[j + h]; wh[j] = a + b; wh[j + h] = a - b; }
  long best_total = 1L << 40; int bestG[8] = {0};
  for (int rep = 0; rep < reps; rep++) {
    int S[64]; int ns = 1; S[0] = 0; int gsel[8]; long sum = wh[0];
    for (int d = 0; d < NC; d++) {
      long bestadd = 1L << 40; int cand[512]; int nc = 0;
      for (int g = 1; g < 512; g++) { int inS = 0; for (int s = 0; s < ns; s++) if (S[s] == g) { inS = 1; break; } if (inS) continue;
        long add = 0; for (int s = 0; s < ns; s++) add += wh[S[s] ^ g];
        if (add < bestadd) { bestadd = add; nc = 0; cand[nc++] = g; } else if (add == bestadd) cand[nc++] = g; }
      int bg = (rep == 0) ? cand[0] : cand[rndi(nc)];
      gsel[d] = bg; sum += bestadd; for (int s = 0; s < ns; s++) S[ns + s] = S[s] ^ bg; ns *= 2;
    }
    int improved = 1;
    while (improved) { improved = 0;
      for (int d = 0; d < NC && !improved; d++) { int R[64]; int nr = 1; R[0] = 0;
        for (int e = 0; e < NC; e++) if (e != d) { for (int s = 0; s < nr; s++) R[nr + s] = R[s] ^ gsel[e]; nr *= 2; }
        long base = 0; for (int s = 0; s < nr; s++) base += wh[R[s]]; long cur = sum - base;
        for (int g = 1; g < 512; g++) { int inR = 0; for (int s = 0; s < nr; s++) if (R[s] == g) { inR = 1; break; } if (inR) continue;
          long add = 0; for (int s = 0; s < nr; s++) add += wh[R[s] ^ g]; if (add < cur) { gsel[d] = g; sum = base + add; improved = 1; break; } } } }
    if (sum / (1<<NC) < best_total) { best_total = sum / (1<<NC); memcpy(bestG, gsel, sizeof(bestG)); }
    if (best_total == 0) break;
  }
  if (G) memcpy(G, bestG, sizeof(bestG));
  return best_total;
}
static void mutate(Circ *c) {
  for (int tries = 0; tries < 100; tries++) {
    int t = rndi(T), i = rndi(3); Tof old = c->t[t][i]; Tof *f = &c->t[t][i];
    int kind = rndi(8);
    if (kind == 0) { f->en = !f->en; if (f->en) { f->a = 1 << rndi(W); f->b = 1 << rndi(W); f->l = 1 << rndi(W); } }
    else if (!f->en) { continue; }
    else if (kind <= 2) f->a ^= 1 << rndi(W);
    else if (kind <= 4) f->b ^= 1 << rndi(W);
    else if (kind <= 6) f->l ^= 1 << rndi(W);
    else { f->a = 1 << rndi(W); f->b = 1 << rndi(W); f->l = 1 << rndi(W); }
    if (f->en && (f->a == 0 || f->b == 0 || f->l == 0)) { *f = old; continue; }
    if (!valid_stage(c->t[t])) { *f = old; continue; }
    return;
  }
}
static int weight(const Circ *c) { int s = 0; for (int t = 0; t < T; t++) for (int i = 0; i < 3; i++) if (c->t[t][i].en) s += __builtin_popcount(c->t[t][i].a) + __builtin_popcount(c->t[t][i].b) + __builtin_popcount(c->t[t][i].l) - 3; return s; }
int main(int argc, char **argv) {
  CLS = argv[1][0] == 'x' ? COLCLS : ROWCLS; T = atoi(argv[2]); double secs = atof(argv[3]); u64 seed = strtoull(argv[4], 0, 10); double temp0 = atof(argv[5]); double wpen = argc > 6 ? atof(argv[6]) : 0.02; NC = argc > 7 ? atoi(argv[7]) : 4;
  rs[0] = seed * 0x9E3779B97F4A7C15ULL + 7; rs[1] = seed ^ 0xD1B54A32D192ED03ULL; for (int i = 0; i < 20; i++) rnd();
  for (int a = 0; a < 64; a++) for (int b = a + 1; b < 64; b++) if (CLS[a] != CLS[b]) { pa[npairs] = a; pb[npairs] = b; npairs++; }
  Circ cur; memset(&cur, 0, sizeof cur);
  u64 w[W]; int G[8]; simulate(&cur, w);
  double cc = best_code(w, G, 3) + wpen * weight(&cur); double bestc = cc; Circ best = cur; long bestcol = 1L << 30;
  clock_t start = clock(); long it = 0;
  while (1) {
    double el = (double)(clock() - start) / CLOCKS_PER_SEC; if ((it & 1023) == 0 && el > secs) break;
    double temp = temp0 * pow(0.001, el / secs) + 0.02;
    Circ nxt = cur; int nm = 1 + rndi(2); for (int m = 0; m < nm; m++) mutate(&nxt);
    simulate(&nxt, w); long col = best_code(w, 0, 2); double nc = col + wpen * weight(&nxt);
    if (nc <= cc || rndf() < exp((cc - nc) / temp)) { cur = nxt; cc = nc;
      if (col < bestcol || (col == bestcol && nc < bestc)) { bestcol = col; bestc = nc; best = cur; fprintf(stderr, "it %ld t=%.1fs col %ld w %d\n", it, el, col, weight(&cur)); } }
    it++;
  }
  simulate(&best, w); long col = best_code(w, G, 20);
  printf("{\"T\":%d,\"col\":%ld,\"stages\":[", T, col);
  for (int t = 0; t < T; t++) { printf("%s[", t ? "," : ""); int first = 1; for (int i = 0; i < 3; i++) { const Tof *f = &best.t[t][i]; if (!f->en) continue; printf("%s[%d,%d,%d]", first ? "" : ",", f->a, f->b, f->l); first = 0; } printf("]"); }
  printf("],\"NC\":%d,\"G\":[", NC); for (int d = 0; d < NC; d++) printf("%s%d", d ? "," : "", G[d]); printf("],\"w\":[");
  for (int k = 0; k < W; k++) printf("%s\"%llx\"", k ? "," : "", (unsigned long long)w[k]); printf("]}\n");
  fprintf(stderr, "done it=%ld col=%ld\n", it, col);
  return 0;
}
