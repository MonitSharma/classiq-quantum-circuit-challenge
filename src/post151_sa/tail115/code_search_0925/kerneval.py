"""kerneval.py xlab.json|cur ylab.json|cur : kernel term estimate for a labeling pair"""
import sys, os, json, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json')
from kterm import table, terms
from codes import COLCLS, ROWCLS, XL, YL
def load(p,side):
    if p=='cur': return XL if side=='x' else YL
    d=json.load(open(p)); return {tuple(map(int,k.split(','))):v for k,v in d['lab'].items()}
def code(side,lab):
    M={'x':48,'y':32}[side]; C={'x':COLCLS,'y':ROWCLS}[side]
    return [ (bin(v&M).count('1')%2) | (lab[(bin(v&M).count('1')%2, C[v])]<<1) for v in range(64)]
def kterms(xl,yl,reps=3):
    T=table(code('x',xl),code('y',yl),4,4)
    if T is None: return None
    return min(terms(T,4,4)[0] for _ in range(reps))
if __name__=='__main__':
    xl=load(sys.argv[1],'x'); yl=load(sys.argv[2],'y')
    print('kernel terms', kterms(xl,yl))
