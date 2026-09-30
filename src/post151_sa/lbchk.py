import pickle, sys, collections
sys.path.insert(0,'.')
R='../../artifacts/118/recipes/'
for side, lname in (('x','x_loader_d44'),('y','y_loader_d46_blkw')):
    D=pickle.load(open(R+lname+'.pkl','rb'))
    S=pickle.load(open(R+side+'_support_89.pkl','rb'))
    lbmasks=set(m for i in range(3) for m,a in S['targets'][i].items() if abs(a)>1e-12)
    rot=[g for g in D['gates'] if g[0][0]=='rz']
    used=collections.Counter(g[0][1] for g in rot)
    print(side, 'lb masks', len(lbmasks), 'rot gates', len(rot), 'distinct masks in loader', len(used))
    print('   loader masks NOT in lb:', sorted(set(used)-lbmasks))
    print('   lb masks NOT in loader:', sorted(lbmasks-set(used)))
    print('   target-index hist of loader rots:', dict(collections.Counter(tgt)))
    # per-target distribution in lb
    print('   lb per target sizes', [sum(1 for m,a in S['targets'][i].items() if abs(a)>1e-12) for i in range(3)])
