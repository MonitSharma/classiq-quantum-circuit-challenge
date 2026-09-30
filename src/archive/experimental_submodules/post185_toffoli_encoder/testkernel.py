import sys, json, math, time
import numpy as np
sys.path.insert(0, 'src')
import two_stage_oracle as ts
from post258_two_stage_anf import decode
from qiskit.quantum_info import Operator
from buildenc import kernel_targets
from post218_beam_phase import psynth
rec = json.load(open('artifacts/185/class_codes.json'))
yl, xl = decode(rec['ylab']), decode(rec['xlab'])
ycode = [((y>>5)&1) | (yl[((y>>5)&1, ts.ROWCLS[y])] << 1) for y in range(64)]
xcode = [(((x&48).bit_count())&1) | (xl[((x&48).bit_count()&1, ts.COLCLS[x])] << 1) for x in range(64)]
targets, terms = kernel_targets(ycode, xcode)
print("targets", len(targets))
want = np.array([math.pi * sum(1 for m in terms if m & ~wd == 0) for wd in range(256)])
for sign in (-0.5, 0.5, -1, 1):
    t0 = time.time()
    kq = psynth(8, {m: sign * a for m, a in targets.items()}, seed=0, beam=16, branch=8)
    d = np.diag(Operator(kq).data)
    ph = np.angle(d * np.exp(-1j * want)); ph -= ph[0]
    ok = np.allclose(np.exp(1j * ph), 1, atol=1e-9)
    print("sign", sign, "ok", ok, "depth", kq.depth(), "cx", kq.count_ops().get('cx', 0), f"{time.time()-t0:.1f}s")
    if ok: break
for params in [dict(seed=209, beam=64, branch=14, alpha=5.0, timew=0.35), dict(seed=1, beam=64, branch=14, alpha=5.0, timew=0.35, horizon=1.0)]:
    t0 = time.time()
    kq = psynth(8, {m: -0.5 * a for m, a in targets.items()}, **params)
    print(params, "depth", kq.depth(), "cx", kq.count_ops().get('cx', 0), f"{time.time()-t0:.1f}s", flush=True)
