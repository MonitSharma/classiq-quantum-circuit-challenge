// Beam search parity-network scheduler for conditional loaders on NV=9 wires.
// Input (stdin): P, then P lines: mask target  (mask over 9 vars; bits 6..8 = targets)
// Params argv: K (beam width), B (branch), seed, lam, mu, nu
// Output: best depth, then gate list lines: "H w" / "R w p" (p = parity index) / "C c t"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define NV 9
#define MAXP 300
#define MAXG 1200
typedef struct { unsigned char type, a, b; short p; } Gate;
typedef struct {
  unsigned short rows[NV];
  unsigned char wt[NV], lastu[NV];
  unsigned char closed;
  unsigned long long rem[5];   // bitset of remaining parities
  short nrem;
  short ng; int parent; // gates stored separately via pool
  int gstart;
  double f;
} State;
int P; unsigned short pmask[MAXP]; unsigned char ptarg[MAXP];
static Gate *gpool; static long gpoolsz=0, gpoolcap=0;
static inline int popc(unsigned x){return __builtin_popcount(x);}
static inline int getb(const State*s,int i){return (s->rem[i>>6]>>(i&63))&1ULL;}
static inline void clrb(State*s,int i){s->rem[i>>6]&=~(1ULL<<(i&63));}
#define TB(i) (1u<<(6+(i)))
#define TMASK (7u<<6)
unsigned rngs=12345; static inline double urand(){rngs=rngs*1103515245u+12345u; return ((rngs>>8)&0xFFFFFF)/16777216.0;}
int openbits(const State*s){int o=0;for(int i=0;i<3;i++) if(!(s->closed>>i&1)) o|=TB(i);return o;}
int allowed(const State*s,int p){ int i=ptarg[p]; if(s->closed>>i&1) return 0; int others=pmask[p]&TMASK&~TB(i); int cl=0; for(int j=0;j<3;j++) if(s->closed>>j&1) cl|=TB(j); return (others&~cl)==0; }
// gate log per state: we store gates in a per-state vector by copying (states small depth ~ few hundred gates)
typedef struct { Gate g[MAXG]; int n; } GLog;
void u3(State*s,GLog*L,int w,int type,int p){ if(!s->lastu[w]){s->wt[w]++; s->lastu[w]=1;} Gate g={type,w,0,p}; L->g[L->n++]=g; }
void cx(State*s,GLog*L,int c,int t){ int tm=(s->wt[c]>s->wt[t]?s->wt[c]:s->wt[t])+1; s->wt[c]=s->wt[t]=tm; s->lastu[c]=s->lastu[t]=0; s->rows[t]^=s->rows[c]; Gate g={2,c,t,-1}; L->g[L->n++]=g; }
// map parity mask -> index lookup
short *pidx; // size 512
void settle(State*s,GLog*L){
  int changed=1;
  while(changed){ changed=0;
    for(int w=0;w<NV;w++){ int p=pidx[s->rows[w]]; if(p>=0 && getb(s,p) && allowed(s,p)){ u3(s,L,w,1,p); clrb(s,p); s->nrem--; changed=1; } }
    for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; int any=0; for(int p=0;p<P;p++) if(ptarg[p]==i && getb(s,p)){any=1;break;} if(any) continue;
      int cnt=0,ww=-1; for(int w=0;w<NV;w++) if(s->rows[w]&TB(i)){cnt++;ww=w;}
      if(cnt==1 && !(s->rows[ww]&openbits(s)&~TB(i))){ u3(s,L,ww,0,-1); s->closed|=1<<i; s->rows[ww]=TB(i); changed=1; }
    }
  }
}
// coordinates of mask in basis rows: gaussian elimination
unsigned coord(const State*s, unsigned m){
  unsigned r[NV], c[NV]; for(int w=0;w<NV;w++){r[w]=s->rows[w]; c[w]=1u<<w;}
  // eliminate
  int piv[NV]; int np=0;
  for(int bit=NV-1;bit>=0;bit--){ int k=-1; for(int w=np;w<NV;w++) if(r[w]>>bit&1){k=w;break;} if(k<0) continue;
    unsigned tr=r[k],tc=c[k]; r[k]=r[np]; c[k]=c[np]; r[np]=tr; c[np]=tc;
    for(int w=0;w<NV;w++) if(w!=np && (r[w]>>bit&1)){ r[w]^=r[np]; c[w]^=c[np]; }
    piv[np]=bit; np++; }
  unsigned res=0; for(int k=0;k<np;k++) if(m>>piv[k]&1) res^=c[k];
  return res;
}
double evalf(const State*s, double lam, double mu, double nu){
  int mx=0; double sum=0; for(int w=0;w<NV;w++){ if(s->wt[w]>mx) mx=s->wt[w]; sum+=s->wt[w]; }
  double dist=0; int ob=openbits(s);
  for(int p=0;p<P;p++) if(getb(s,p)){ unsigned C=coord(s,pmask[p]); int d=popc(C)-1; dist+= d; }
  // stray bits of finished targets
  double stray=0; for(int i=0;i<3;i++){ if(s->closed>>i&1) continue; int any=0; for(int p=0;p<P;p++) if(ptarg[p]==i&&getb(s,p)){any=1;break;} int cnt=0; for(int w=0;w<NV;w++) if(s->rows[w]&TB(i)) cnt++; stray += (any?0.4:1.0)*(cnt-1); }
  return mx + lam*sum/NV + mu*s->nrem + nu*dist + stray;
}
typedef struct { State s; GLog L; } Node;
int cmpf(const void*a,const void*b){ double fa=((Node*)a)->s.f, fb=((Node*)b)->s.f; return fa<fb?-1:fa>fb; }
int main(int argc,char**argv){
  int K=atoi(argv[1]), B=atoi(argv[2]); rngs=atoi(argv[3]); double lam=atof(argv[4]), mu=atof(argv[5]), nu=atof(argv[6]); double noise=argc>7?atof(argv[7]):0.0;
  if(scanf("%d",&P)!=1) return 1;
  pidx=malloc(sizeof(short)*512); for(int i=0;i<512;i++) pidx[i]=-1;
  for(int p=0;p<P;p++){ int m,t; scanf("%d %d",&m,&t); pmask[p]=m; ptarg[p]=t; pidx[m]=p; }
  Node *beam=malloc(sizeof(Node)*K), *next=malloc(sizeof(Node)*K*B+16);
  memset(&beam[0],0,sizeof(Node));
  State *s0=&beam[0].s; for(int w=0;w<NV;w++) s0->rows[w]=1u<<w; s0->nrem=P; for(int p=0;p<P;p++) s0->rem[p>>6]|=1ULL<<(p&63);
  for(int i=0;i<3;i++) u3(s0,&beam[0].L,6+i,0,-1);
  settle(s0,&beam[0].L);
  int nb=1; int bestd=100000; Node *best=malloc(sizeof(Node)); int found=0;
  for(int step=0; step<1100 && nb>0; step++){
    int nn=0;
    for(int bi=0;bi<nb;bi++){
      State *s=&beam[bi].s; int ob=openbits(s);
      if(s->closed==7){ int mx=0; for(int w=0;w<NV;w++) if(s->wt[w]>mx) mx=s->wt[w]; if(mx<bestd){bestd=mx; *best=beam[bi]; found=1;} continue; }
      // score moves
      double sc[NV*NV]; int mc[NV*NV], mt[NV*NV]; int nm=0;
      unsigned Cs[MAXP]; int ncs=0; for(int p=0;p<P;p++) if(getb(s,p)&&allowed(s,p)) Cs[ncs++]=coord(s,pmask[p]);
      int tmin=255; for(int c=0;c<NV;c++) for(int t=0;t<NV;t++) if(c!=t){int tm=s->wt[c]>s->wt[t]?s->wt[c]:s->wt[t]; if(tm<tmin) tmin=tm;}
      for(int c=0;c<NV;c++) for(int t=0;t<NV;t++){ if(c==t) continue; unsigned nw=s->rows[t]^s->rows[c];
        if(popc(nw&ob)>1) continue;
        // forbid adding bit of finished-open target
        int bad=0; for(int i=0;i<3;i++){ if(!(ob&TB(i))) continue; int any=0; for(int p=0;p<P;p++) if(ptarg[p]==i&&getb(s,p)){any=1;break;} if(!any && (nw&TB(i)) && !(s->rows[t]&TB(i))) bad=1; }
        if(bad) continue;
        int p=pidx[nw]; double v=0; if(p>=0 && getb(s,p) && allowed(s,p)) v+=10;
        for(int i=0;i<3;i++){ if(!(ob&TB(i))) continue; int any=0; for(int q=0;q<P;q++) if(ptarg[q]==i&&getb(s,q)){any=1;break;} if(!any && (s->rows[t]&TB(i)) && !(nw&TB(i))) v+=8; }
        int tm=s->wt[c]>s->wt[t]?s->wt[c]:s->wt[t]; v-=1.0*(tm-tmin);
        { double dd=0; for(int k=0;k<ncs;k++){ unsigned C=Cs[k]; if(C>>t&1){ int pc=popc(C); int pc2=(C>>c&1)?pc-1:pc+1; double w1=1.0/(pc), w2=1.0/(pc2); dd+= (w2-w1); } } v+=6.0*dd; }
        { int cl=0; for(int i=0;i<3;i++){ if(!(ob&TB(i))) continue; int any=0; for(int q=0;q<P;q++) if(ptarg[q]==i&&getb(s,q)){any=1;break;} if(!any && (s->rows[t]&TB(i)) && !(nw&TB(i))) cl=1; } if(cl) v+=1000; }
        v+=noise*urand();
        sc[nm]=v; mc[nm]=c; mt[nm]=t; nm++; }
      int forced=0; { int maxsc=-1000; for(int k=0;k<nm;k++) if(sc[k]>maxsc) maxsc=sc[k]; }
      // pick top B by sc, but always include all hits
      { for(int k=0;k<nm;k++) if(sc[k]>500) forced=1; }
      for(int k=0;k<nm && k<B;k++){ if(forced && k>0) { int bk2=k; for(int j=k;j<nm;j++) if(sc[j]>sc[bk2]) bk2=j; if(sc[bk2]<500) break; } int bk=k; for(int j=k+1;j<nm;j++) if(sc[j]>sc[bk]) bk=j; double tv=sc[k]; sc[k]=sc[bk]; sc[bk]=tv; int ti=mc[k]; mc[k]=mc[bk]; mc[bk]=ti; ti=mt[k]; mt[k]=mt[bk]; mt[bk]=ti;
        Node *nd=&next[nn++]; nd->s=*s; nd->L=beam[bi].L; cx(&nd->s,&nd->L,mc[k],mt[k]); settle(&nd->s,&nd->L);
        if(nd->L.n>MAXG-50){ nn--; continue; }
        nd->s.f=evalf(&nd->s,lam,mu,nu)+noise*0.01*urand();
        if(forced) nd->s.f-=1000; }
    }
    if(nn==0){fprintf(stderr,"no children at step %d\n",step); break;}
    qsort(next,nn,sizeof(Node),cmpf);
    // dedupe by rows+rem
    int kept=0;
    for(int i=0;i<nn && kept<K;i++){ int dup=0; for(int j=0;j<kept;j++){ if(memcmp(beam[j].s.rows,next[i].s.rows,sizeof(next[i].s.rows))==0 && memcmp(beam[j].s.rem,next[i].s.rem,sizeof(next[i].s.rem))==0 && beam[j].s.closed==next[i].s.closed){dup=1;break;} } if(!dup) beam[kept++]=next[i]; }
    nb=kept; if(0) {fprintf(stderr,"step %d nb %d best f %.2f nrem %d closed %d rem:",step,nb,beam[0].s.f,beam[0].s.nrem,beam[0].s.closed); for(int p=0;p<P;p++) if(getb(&beam[0].s,p)&&allowed(&beam[0].s,p)) fprintf(stderr," %x/t%d",pmask[p],ptarg[p]); fprintf(stderr," rows:"); for(int w=0;w<NV;w++) fprintf(stderr," %x",beam[0].s.rows[w]); fprintf(stderr,"\n");}
    // early prune: states whose current max wt >= bestd
    int w2=0; for(int i=0;i<nb;i++){ int mx=0; for(int w=0;w<NV;w++) if(beam[i].s.wt[w]>mx) mx=beam[i].s.wt[w]; if(mx<bestd) beam[w2++]=beam[i]; } nb=w2;
  }
  if(!found){ printf("FAIL\n"); return 0; }
  printf("%d\n",bestd);
  for(int i=0;i<best->L.n;i++){ Gate g=best->L.g[i]; if(g.type==0) printf("H %d\n",g.a); else if(g.type==1) printf("R %d %d\n",g.a,g.p); else printf("C %d %d\n",g.a,g.b); }
  return 0;
}
