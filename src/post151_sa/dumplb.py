import pickle, sys
def dump(pkl, out):
    D=pickle.load(open(pkl,'rb'))
    pl=[(m,i) for i in range(3) for m,a in D['targets'][i].items() if abs(a)>1e-12]
    lines=[str(len(pl))]+[f'{m} {i}' for m,i in pl]+[str(len(D['req']))]+[str(v) for v in D['req']]+['0']
    open(out,'w').write('\n'.join(lines)+'\n')
    seq=[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']
    return len(pl), len(seq), D['req'], seq
if __name__=='__main__':
    n,ncx,req,seq=dump(sys.argv[1],sys.argv[2])
    print(sys.argv[2],'terms',n,'ncx',ncx,'req',req)
    if len(sys.argv)>3 and seq:
        open(sys.argv[3],'w').write('0 %d\n'%len(seq)+'\n'.join('%d %d'%ct for ct in seq)+'\n')
