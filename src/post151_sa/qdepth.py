import re,sys
def stats(path):
    src=open(path).read()
    st=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()]
    t=[0]*18; cx=0; u=0
    for s in st[3:]:
        m=re.fullmatch(r"u3\s*\(([^,]+),([^,]+),([^,]+)\)\s+q\s*\[\s*(\d+)\s*\]",s)
        if m: w=int(m.group(4)); t[w]+=1; u+=1; continue
        m=re.fullmatch(r"cx\s+q\s*\[\s*(\d+)\s*\]\s*,\s*q\s*\[\s*(\d+)\s*\]",s)
        if m:
            a,b=int(m.group(1)),int(m.group(2)); n=max(t[a],t[b])+1; t[a]=t[b]=n; cx+=1; continue
        raise ValueError(s)
    return max(t),cx,u
if __name__=='__main__':
    for p in sys.argv[1:]:
        d,c,u=stats(p); print(p,'depth',d,'cx',c,'u3',u)
