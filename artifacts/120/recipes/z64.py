"""Incremental linear solver over Z/2^K (Howell form)."""
def val(a,MOD=64):
    a%=MOD
    if a==0: return 64
    v=0
    while a%2==0: a//=2; v+=1
    return v
def inv_unit(u,MOD):
    return pow(u%MOD,-1,MOD)
class Sys:
    def __init__(self,n,MOD=64,K=6):
        self.n=n; self.MOD=MOD; self.K=K; self.rows=[]
    def _insert(self,rows,a,b):
        """returns False on inconsistency; rows modified in place (Howell)."""
        M=self.MOD; K=self.K
        stack=[(a,b)]
        while stack:
            a,b=stack.pop()
            a=[x%M for x in a]; b=b%M
            while True:
                j=-1
                for k in range(self.n):
                    if a[k]: j=k; break
                if j<0:
                    if b: return False
                    break
                idx=-1
                for t in range(len(rows)):
                    if rows[t][2]==j: idx=t; break
                if idx<0:
                    rows.append((a,b,j)); rows.sort(key=lambda z:z[2])
                    d=val(a[j],M)
                    if d>0:
                        s=1<<(K-d)
                        stack.append(([x*s%M for x in a],b*s%M))
                    break
                v,r,p=rows[idx]
                va=val(a[j],M); vp=val(v[j],M)
                if va>=vp:
                    mm=M>>vp
                    f=((a[j]>>vp)*inv_unit(v[j]>>vp,mm))%mm
                    a=[(a[k]-f*v[k])%M for k in range(self.n)]; b=(b-f*r)%M
                else:
                    rows[idx]=(a,b,j)
                    d=val(a[j],M)
                    if d>0:
                        s=1<<(K-d)
                        stack.append(([x*s%M for x in a],b*s%M))
                    a=list(v); b=r
        return True
    def add(self,a,b):
        rows=[(list(v),r,p) for v,r,p in self.rows]
        if not self._insert(rows,a,b): return False
        self.rows=rows; return True
    def solve(self):
        M=self.MOD; x=[0]*self.n
        for v,r,p in reversed(self.rows):
            s=(r-sum(v[k]*x[k] for k in range(p+1,self.n)))%M
            d=val(v[p],M)
            if d>=64:
                if s%M: return None
                continue
            if s%(1<<d): return None
            mm=M>>d
            x[p]=((s>>d)*inv_unit(v[p]>>d,mm))%mm
        for v,r,p in self.rows:
            if sum(v[k]*x[k] for k in range(self.n))%M != r%M: return None
        return x
