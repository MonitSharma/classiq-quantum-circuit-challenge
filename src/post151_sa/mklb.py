"""Dump the 118 support frames to .lb beam inputs."""
import pickle, sys
sys.path.insert(0,'.')
from mkD3 import dump
R='../../artifacts/118/recipes/'
for f,tag in (('x_support_89','s118x'),('y_support_89','s118y')):
    D=pickle.load(open(R+f+'.pkl','rb'))
    print(tag, dump(D,tag))
