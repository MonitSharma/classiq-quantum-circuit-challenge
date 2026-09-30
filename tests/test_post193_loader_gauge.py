"""Validate the symbolic input phase used to match asymmetric loaders."""
import json,math
from pathlib import Path
import numpy as np
import pytest
from qiskit.quantum_info import Statevector
from post193_asymmetric_loaders import gauge
from post224_relative_lookup import relative
from post258_two_stage_anf import decode
import two_stage_oracle as ts

@pytest.mark.parametrize('side,seed',[(0,0),(0,99),(1,37),(1,155)])
def test_symbolic_gauge_matches_loader(side,seed):
 c=json.loads(Path('artifacts/193/class_codes.json').read_text());cls=ts.COLCLS if side else ts.ROWCLS;mask=48 if side else 32;lab=decode(c['xlab' if side else 'ylab'])
 values=[lab[((v&mask).bit_count()%2,k)] for v,k in enumerate(cls)];table=math.pi*np.array([[v>>b&1 for v in values] for b in range(3)])
 want=np.exp(1j*math.pi*np.array(gauge(table,values,seed))/128);q,_=relative(table,seed);observed=[]
 for v in range(64):
  state=Statevector.from_int(v,512).evolve(q).data;w=v|(values[v]<<6);assert abs(state[w])>1-1e-10;observed.append(state[w])
 observed=np.array(observed);phase=observed[0]/abs(observed[0]);assert np.max(abs(observed-phase*want))<1e-10
