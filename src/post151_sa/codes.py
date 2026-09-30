import json, numpy as np
from logo import logo_pixel
def classes():
    rows, rowcls = {}, [0]*64
    for y in range(64):
        rowcls[y] = rows.setdefault(tuple(1 if logo_pixel(x,y) else 0 for x in range(64)), len(rows))
    cols, colcls = {}, [0]*64
    for x in range(64):
        colcls[x] = cols.setdefault(tuple(1 if logo_pixel(x,y) else 0 for y in range(64)), len(cols))
    return rowcls, colcls
ROWCLS, COLCLS = classes()
import os
cc=json.load(open(os.environ.get('CLASS_CODES','artifacts/185/class_codes.json')))
dec=lambda lab:{tuple(map(int,k.split(','))):v for k,v in lab.items()}
XL=dec(cc['xlab']); YL=dec(cc['ylab'])
xcode=[XL[(bin(v&48).count('1')%2, COLCLS[v])] for v in range(64)]
ycode=[YL[(bin(v&32).count('1')%2, ROWCLS[v])] for v in range(64)]
def bits(code): return np.array([[ (c>>b)&1 for c in code] for b in range(3)])
H=np.array([[1]])
for _ in range(6): H=np.block([[H,H],[H,-H]])
# H[s,z] = (-1)^{popcount(s&z)} (Sylvester ordering matches bit indices)
