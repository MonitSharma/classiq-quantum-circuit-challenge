"""tailcnf.py SRC.pkl A WN SPEC OUT.cnf [MODEL.sol] [FREEK]
Build (or decode) the x-loader tail SAT used in the depth-114 search.
- Window: layers A+1 .. A+WN of the loader SRC (the part after it is re-synthesized).
- SPEC: JSON, e.g. '{"idle":{"0":1,"1":5}}' = px idle in the last layer (ready <= 42), Lx0 idle in the last 5.
  req index order is [px 48, Lx0 64, Lx1 128, x12 256].
- FREEK (optional, default 0): number of FREE CX layers before the window (no rotations, no closings,
  the Lx0 wire not used). It is a relaxation: "could a re-arranged state at layer A finish by A+WN?"
Without MODEL: writes OUT.cnf. With MODEL (a kissat output containing 's SATISFIABLE' and 'v' lines):
decodes it, checks the loader with sim.check_loader2 and writes OUT.cnf.pkl (a loader pickle).
Optional environment settings (use the same settings when decoding):
SAT_ROW_ENCODING=direct avoids auxiliary row-update variables; SAT_EXACT_ONCE=1
requires each phase once; SAT_EAGER=1 also emits phases at their first eligible idle slot.
The eager option is a restricted search, so its UNSAT results must be labelled accordingly.
SAT_PROJ=<bitmask> builds the projected RELAXATION (rows kept only on those bits; only UNSAT is meaningful).
SAT_SYM=1 adds satisfiability-preserving ASAP symmetry breaking (satwin3 `sym`); not allowed with FREEK > 0.
Run from anywhere; paths are relative to this repository."""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SA = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, SA)
os.environ.setdefault('CLASS_CODES', os.path.join(SA, '../../artifacts/185/class_codes.json'))
os.environ.setdefault('CLASSIQ_ROOT', os.path.join(SA, '../..'))
import satwin3 as S
src, a, Wn0, spec, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), json.loads(sys.argv[4]), sys.argv[5]
model = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != '-' else None
k = int(sys.argv[7]) if len(sys.argv) > 7 else 0
D = pickle.load(open(src, 'rb')); pl, pidx = S.plist_of(D)
g = D['gates'] + [(('cx',), c, t) for c, t in D.get('fix', [])]
layers = S.layerize(g); states, recs = S.replay(layers, len(layers), pidx, pl); n = len(recs)
req = list(D['req']); fin = states[n][0]
if 384 in req and 384 not in fin: req = [256 if r == 384 else r for r in req]
Wn = Wn0 + k; NV = 9
if k and os.environ.get('SAT_SYM', '0') == '1': raise SystemExit('SAT_SYM is not valid with FREEK > 0')
rows0, cl0, dn0 = states[a]; rows1, cl1, dn1 = states[n]
nP = len(dn1 - dn0); nC = len(cl1 - cl0)
bX = (Wn + 1) * NV * NV; bR = bX + Wn * NV * (NV - 1); bH = bR + Wn * NV * nP
EXTRA = []
Lw = [w for w in range(NV) if rows0[w] == 64]
for j in range(k):
    for w in range(NV):
        for q in range(nP): EXTRA.append([-(bR + 1 + (j * NV + w) * nP + q)])
        for c in range(nC): EXTRA.append([-(bH + 1 + (j * NV + w) * nC + c)])
    for c in range(NV):
        for t in range(NV):
            if c != t and (c in Lw or t in Lw): EXTRA.append([-(bX + 1 + j * NV * (NV - 1) + c * (NV - 1) + (t if t < c else t - 1))])
def solve(self, timeout=60):
    for c in EXTRA: self.add(c)
    if model is None:
        with open(out, 'w') as f:
            f.write("p cnf %d %d\n" % (self.n, len(self.cl)))
            for c in self.cl: f.write(" ".join(map(str, c)) + " 0\n")
        print('wrote', out, 'vars', self.n, 'clauses', len(self.cl)); return None
    txt = open(model, errors='ignore').read()
    if 's SATISFIABLE' not in txt: print('model file is not SATISFIABLE'); return None
    val = set()
    for line in txt.split('\n'):
        if line.startswith('v '):
            for x in line[2:].split():
                x = int(x)
                if x > 0: val.add(x)
    violated = [i for i,c in enumerate(self.cl)
                if not any((x in val) if x > 0 else (-x not in val) for x in c)]
    if violated:
        raise ValueError('SAT assignment violates %d regenerated clauses; check encoding settings' % len(violated))
    return val
S.CNF.solve = solve
idle = {int(kk): v for kk, v in spec.get('idle', {}).items()}
res = S.solve_window(pl, states[a], states[n], recs[a:n], Wn, final=True, req=req, al=D['al'], timeout=10, idle_last=idle,
                     row_encoding=os.environ.get('SAT_ROW_ENCODING', 'aux'),
                     exact_once=os.environ.get('SAT_EXACT_ONCE', '0') == '1',
                     eager_rotations=os.environ.get('SAT_EAGER', '0') == '1',
                     sym=os.environ.get('SAT_SYM', '0') == '1',
                     proj=int(os.environ['SAT_PROJ'], 0) if os.environ.get('SAT_PROJ') else None)
if res:
    if k: print('free layers', res[:k]); res = res[k:]
    from sim import check_loader2
    newrecs = recs[:a] + res; g2 = S.recs_to_gates(newrecs, pl); chk = check_loader2(g2, D['newcode'])
    print('decoded; loader max_dev %.1e' % chk['max_dev'])
    if chk['max_dev'] > 1e-9:
        raise ValueError('decoded loader failed verification; no pickle written')
    D2 = dict(D); D2['gates'] = g2; D2['fix'] = []; D2['req'] = req; pickle.dump(D2, open(out + '.pkl', 'wb')); print('saved', out + '.pkl')
    for j, L in enumerate(res): print(a + 1 + j, L)
