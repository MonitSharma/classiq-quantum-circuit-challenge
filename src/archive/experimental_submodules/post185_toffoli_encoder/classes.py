import numpy as np
from logo import M
def classes_of(mat):
    d = {}; cls = []
    for r in mat:
        cls.append(d.setdefault(tuple(r), len(d)))
    return cls
ROWCLS = classes_of(M)        # function of y
COLCLS = classes_of(M.T)      # function of x
