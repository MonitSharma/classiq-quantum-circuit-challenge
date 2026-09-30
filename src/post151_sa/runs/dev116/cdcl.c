// Compact CDCL SAT solver: 2WL, 1UIP learning with minimization, VSIDS heap, phase saving,
// Luby restarts, LBD-based learnt clause reduction.  Usage: cdcl file.cnf [out.sol] [maxseconds]
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef struct { int *d; int n, cap; } vec;
static void vpush(vec *v, int x){ if(v->n==v->cap){ v->cap=v->cap?v->cap*2:4; v->d=realloc(v->d,sizeof(int)*v->cap);} v->d[v->n++]=x; }
// clause arena: [size, lbd|learnt<<31? , activity(float bits), lits...]
static int *A; static long An=0, Acap=0;
#define CSZ(c) A[c]
#define CFLG(c) A[(c)+1]     // bit0 learnt, bit1 deleted, bits 2.. lbd
#define CACT(c) (*(float*)&A[(c)+2])
#define CL(c) (&A[(c)+3])
static int nv, nc;
static vec *W;              // watches indexed by lit index (2*v + sign)
static signed char *val;    // per var: 0 unassigned, 1 true, -1 false
static int *lev, *rsn, *trail, tn=0, *tlim, dl=0, qhead=0;
static double *act; static double vinc=1.0; static float cinc=1.0f;
static int *heap, hn=0, *hpos; static signed char *phase; static char *seen;
static vec learnts;
static inline int L2I(int l){ return l>0 ? 2*l : 2*(-l)+1; }
static inline int lval(int l){ int v=val[abs(l)]; return l>0? v : -v; }
static void hup(int i){ int x=heap[i]; while(i>0){ int p=(i-1)/2; if(act[heap[p]]>=act[x]) break; heap[i]=heap[p]; hpos[heap[i]]=i; i=p; } heap[i]=x; hpos[x]=i; }
static void hdown(int i){ int x=heap[i]; for(;;){ int c=2*i+1; if(c>=hn) break; if(c+1<hn && act[heap[c+1]]>act[heap[c]]) c++; if(act[heap[c]]<=act[x]) break; heap[i]=heap[c]; hpos[heap[i]]=i; i=c; } heap[i]=x; hpos[x]=i; }
static void hins(int v){ if(hpos[v]>=0) return; heap[hn]=v; hpos[v]=hn; hn++; hup(hn-1); }
static int hpop(void){ int v=heap[0]; hn--; hpos[v]=-1; if(hn>0){ heap[0]=heap[hn]; hpos[heap[0]]=0; hdown(0);} return v; }
static void bump(int v){ act[v]+=vinc; if(act[v]>1e100){ for(int i=1;i<=nv;i++) act[i]*=1e-100; vinc*=1e-100; } if(hpos[v]>=0) hup(hpos[v]); }
static long newclause(int *lits, int n, int learnt){
  if(An+n+3>Acap){ Acap=(An+n+3)*2; A=realloc(A,sizeof(int)*Acap); }
  long c=An; A[c]=n; A[c+1]=learnt?1:0; CACT(c)=0; memcpy(&A[c+3],lits,sizeof(int)*n); An+=n+3; return c; }
static void watch(long c){ vpush(&W[L2I(-CL(c)[0])],(int)c); vpush(&W[L2I(-CL(c)[1])],(int)c); }
static void assign(int l, int r){ int v=abs(l); val[v]=l>0?1:-1; lev[v]=dl; rsn[v]=r; trail[tn++]=l; }
static long propagate(void){
  while(qhead<tn){
    int p=trail[qhead++]; // p became true; visit clauses watching -p i.e. W[L2I(p)] holds clauses where -p... we store watch at index of negation of watched lit
    vec *ws=&W[L2I(p)]; int i=0,j=0;
    while(i<ws->n){
      long c=ws->d[i++]; int *ls=CL(c);
      if(CFLG(c)&2) continue; // deleted
      if(ls[0]==-p){ ls[0]=ls[1]; ls[1]=-p; }
      if(lval(ls[0])==1){ ws->d[j++]=(int)c; continue; }
      int n=CSZ(c), found=0;
      for(int k=2;k<n;k++) if(lval(ls[k])!=-1){ ls[1]=ls[k]; ls[k]=-p; vpush(&W[L2I(-ls[1])],(int)c); found=1; break; }
      if(found) continue;
      ws->d[j++]=(int)c;
      if(lval(ls[0])==-1){ while(i<ws->n) ws->d[j++]=ws->d[i++]; ws->n=j; qhead=tn; return c; }
      assign(ls[0],(int)c);
    }
    ws->n=j;
  }
  return -1;
}
static int *lbuf; static int *stk; static int *mclear; static int mcn=0;
static int redundant(int l, unsigned levmask){ // simple recursive minimization
  int top=0; stk[top++]=l; int base=mcn;
  while(top){ int x=stk[--top]; long c=rsn[abs(x)]; int *ls=CL(c); int n=CSZ(c);
    for(int k=0;k<n;k++){ int q=ls[k]; int v=abs(q); if(v==abs(x)) continue; if(seen[v]||lev[v]==0) continue;
      if(rsn[v]>=0 && (levmask>>(lev[v]&31)&1)){ seen[v]=1; stk[top++]=q; mclear[mcn++]=v; }
      else { for(int t=base;t<mcn;t++) seen[mclear[t]]=0; mcn=base; return 0; } } }
  return 1; }
static int analyze(long confl, int *out_n, int *btlev, int *lbd){
  int pathC=0, p=0, idx=tn-1, n=1; lbuf[0]=0;
  do{
    int *ls=CL(confl); int sz=CSZ(confl);
    if(CFLG(confl)&1){ CACT(confl)+=cinc; }
    for(int k=(p==0?0:1);k<sz;k++){ int q=ls[k]; int v=abs(q);
      if(!seen[v] && lev[v]>0){ seen[v]=1; bump(v); if(lev[v]>=dl) pathC++; else lbuf[n++]=q; } }
    while(!seen[abs(trail[idx])]) idx--;
    p=trail[idx]; confl=rsn[abs(p)]; seen[abs(p)]=0; pathC--; idx--;
  }while(pathC>0);
  lbuf[0]=-p;
  // minimize
  unsigned mask=0; for(int k=1;k<n;k++) mask|=1u<<(lev[abs(lbuf[k])]&31);
  for(int k=1;k<n;k++) mclear[mcn++]=abs(lbuf[k]);
  int j=1; for(int k=1;k<n;k++){ int v=abs(lbuf[k]); if(rsn[v]<0 || !redundant(lbuf[k],mask)) lbuf[j++]=lbuf[k]; }
  for(int t=0;t<mcn;t++) seen[mclear[t]]=0; mcn=0;
  n=j;
  // clear seen of minimization marks (redundant() leaves marks for successful ones) -> brute clear
  // compute backtrack level
  int bt=0, mi=1; for(int k=1;k<n;k++) if(lev[abs(lbuf[k])]>bt){ bt=lev[abs(lbuf[k])]; mi=k; }
  if(n>1){ int t=lbuf[1]; lbuf[1]=lbuf[mi]; lbuf[mi]=t; }
  // lbd
  static int *lvseen=0; static int stamp=0; if(!lvseen) lvseen=calloc(nv+2,sizeof(int)); stamp++;
  int L=0; for(int k=0;k<n;k++){ int lv=lev[abs(lbuf[k])]; if(lvseen[lv]!=stamp){ lvseen[lv]=stamp; L++; } }
  *out_n=n; *btlev=bt; *lbd=L; return 0; }
static void backtrack(int lvl){ if(dl<=lvl) return; for(int i=tn-1;i>=tlim[lvl+1];i--){ int v=abs(trail[i]); phase[v]=val[v]; val[v]=0; rsn[v]=-1; hins(v);} tn=tlim[lvl+1]; qhead=tn; dl=lvl; }
static double luby(double y,int x){ int size,seq; for(size=1,seq=0;size<x+1;seq++,size=2*size+1); while(size-1!=x){ size=(size-1)>>1; seq--; x=x%size; } double r=1; for(int i=0;i<seq;i++) r*=y; return r; }
static int cmp_learnt(const void*a,const void*b){ long x=*(int*)a,y=*(int*)b; int lx=CFLG(x)>>2, ly=CFLG(y)>>2; if(lx!=ly) return ly-lx; float ax=CACT(x), ay=CACT(y); return ax<ay?-1:ax>ay?1:0; }
static void reduce(void){
  qsort(learnts.d,learnts.n,sizeof(int),cmp_learnt); int half=learnts.n/2, j=0;
  for(int i=0;i<learnts.n;i++){ long c=learnts.d[i]; int locked = (rsn[abs(CL(c)[0])]==(int)c && lval(CL(c)[0])==1);
    if(i<half && (CFLG(c)>>2)>2 && !locked && CSZ(c)>2) CFLG(c)|=2; else learnts.d[j++]=(int)c; }
  learnts.n=j; }
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); char line[1<<16]; int *lits=malloc(sizeof(int)*(1<<20)); int ln=0;
  double maxsec=argc>3?atof(argv[3]):1e18; clock_t t0=clock();
  // header
  while(fgets(line,sizeof line,f)){ if(line[0]=='c') continue; if(line[0]=='p'){ sscanf(line,"p cnf %d %d",&nv,&nc); break; } }
  W=calloc(2*nv+4,sizeof(vec)); val=calloc(nv+1,1); lev=calloc(nv+1,sizeof(int)); rsn=malloc(sizeof(int)*(nv+1)); for(int i=0;i<=nv;i++) rsn[i]=-1;
  trail=malloc(sizeof(int)*(nv+1)); tlim=malloc(sizeof(int)*(nv+2)); act=calloc(nv+1,sizeof(double)); heap=malloc(sizeof(int)*(nv+1)); hpos=malloc(sizeof(int)*(nv+1));
  phase=malloc(nv+1); memset(phase,-1,nv+1); seen=calloc(nv+1,1); lbuf=malloc(sizeof(int)*(nv+1)); stk=malloc(sizeof(int)*(nv+1)*2); mclear=malloc(sizeof(int)*(nv+1)*2);
  unsigned long long rs=88172645463325252ull^(argc>4?strtoull(argv[4],0,10)*0x9E3779B97F4A7C15ull:0); for(int v=1;v<=nv;v++){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; act[v]=(argc>4)?(rs%1000)*1e-6:0; }
  for(int i=0;i<=nv;i++) hpos[i]=-1; for(int v=1;v<=nv;v++) hins(v);
  int x, unsat=0;
  while(fscanf(f,"%d",&x)==1){
    if(x){ lits[ln++]=x; continue; }
    // dedupe & tautology
    int n=0, taut=0; for(int i=0;i<ln;i++){ int dup=0; for(int j=0;j<n;j++){ if(lits[j]==lits[i]) dup=1; if(lits[j]==-lits[i]) taut=1; } if(!dup) lits[n++]=lits[i]; }
    ln=0; if(taut) continue;
    if(n==0){ unsat=1; continue; }
    if(n==1){ if(lval(lits[0])==-1) unsat=1; else if(lval(lits[0])==0) assign(lits[0],-1); continue; }
    long c=newclause(lits,n,0); watch(c);
  }
  fclose(f);
  if(unsat || propagate()>=0){ printf("s UNSATISFIABLE\n"); return 20; }
  long conflicts=0, nextreduce=4000; int restarts=0, nred=0; double rbase=100; long rlimit=(long)(rbase*luby(2,0));
  long rc=0;
  for(;;){
    long confl=propagate();
    if(confl>=0){
      conflicts++; rc++;
      if(dl==0){ printf("s UNSATISFIABLE\n"); fflush(stdout); return 20; }
      int n,bt,lbd; analyze(confl,&n,&bt,&lbd);
      backtrack(bt);
      if(n==1){ assign(lbuf[0],-1); }
      else { long c=newclause(lbuf,n,1); CFLG(c)|=lbd<<2; watch(c); vpush(&learnts,(int)c); CACT(c)=cinc; assign(lbuf[0],(int)c); }
      vinc*=1.0/0.95; cinc*=1.0f/0.999f; if(cinc>1e20f){ for(int i=0;i<learnts.n;i++) CACT(learnts.d[i])*=1e-20f; cinc*=1e-20f; }
      if(conflicts%10000==0){ double el=(double)(clock()-t0)/CLOCKS_PER_SEC; fprintf(stderr,"c conflicts %ld restarts %d learnts %d trail0 %d  %.0fs\n",conflicts,restarts,learnts.n,dl==0?tn:tlim[1],el); if(el>maxsec){ printf("s UNKNOWN\n"); return 0; } }
    } else {
      if(rc>=rlimit){ restarts++; rc=0; rlimit=(long)(rbase*luby(2,restarts)); backtrack(0); }
      if(conflicts>=nextreduce){ nred++; nextreduce=conflicts+4000+600*(long)nred; reduce(); }
      int v=0; while(hn>0){ int c=hpop(); if(!val[c]){ v=c; break; } }
      if(!v){ // SAT
        printf("s SATISFIABLE\n"); FILE*o=argc>2?fopen(argv[2],"w"):stdout; for(int i=1;i<=nv;i++) fprintf(o,"%d ",val[i]>0?i:-i); fprintf(o,"0\n"); if(o!=stdout) fclose(o); return 10; }
      tlim[++dl]=tn; assign(phase[v]>0? v : -v, -1);
    }
  }
}
