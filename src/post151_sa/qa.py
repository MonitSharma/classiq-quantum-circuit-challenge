import re, sys, collections
def parse(path):
    src=open(path).read()
    st=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()]
    n=int(re.search(r"qreg q\[(\d+)\]",src).group(1))
    gates=[]
    for s in st[3:]:
        m=re.fullmatch(r"u3\s*\(([^)]*)\)\s+q\[(\d+)\]",s)
        if m: gates.append(('u',(int(m.group(2)),),m.group(1))); continue
        m=re.fullmatch(r"cx\s+q\[(\d+)\]\s*,\s*q\[(\d+)\]",s)
        if m: gates.append(('cx',(int(m.group(1)),int(m.group(2))),None)); continue
        raise ValueError(s)
    return n,gates
def layers(n,gates):
    d=[0]*n; L=[]
    for g in gates:
        l=max(d[q] for q in g[1])+1
        for q in g[1]: d[q]=l
        L.append(l)
    return max(d),L
if __name__=="__main__":
    n,g=parse(sys.argv[1]); D,L=layers(n,g)
    print("depth",D,"cx",sum(1 for x in g if x[0]=='cx'),"u3",sum(1 for x in g if x[0]=='u'))
    # occupancy per layer
    occ=collections.defaultdict(lambda:['.']*n)
    for gg,l in zip(g,L):
        for q in gg[1]:
            occ[l][q]= 'c' if gg[0]=='cx' else 'u'
    for l in range(1,D+1):
        row=occ[l]; print(f"{l:3d} {''.join(row)}  busy={sum(1 for c in row if c!='.')}")
