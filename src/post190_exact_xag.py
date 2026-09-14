"""Exact shared-XAG synthesis via CNF (pysat).

Signals: 6 inputs, then k AND nodes. Each AND input is an XOR of earlier
signals (+ optional constant). Each output is an XOR of any signals (+ const).
XOR/NOT free; AND nodes are the cost. Returns a witness or UNSAT.
"""
import sys, json, time
from pysat.formula import IDPool
from pysat.solvers import Cadical153

NR = 64

def xor_chain(cnf, pool, lits, const):
    """Tseitin XOR of lits (+const). Returns a literal (or None for constant)."""
    acc = None
    for l in lits:
        if acc is None:
            acc = l; continue
        z = pool.id()
        cnf += [[-acc, -l, -z], [acc, l, -z], [acc, -l, z], [-acc, l, z]]
        acc = z
    if acc is None:
        return ('const', 1 if const else 0)
    if const:
        z = pool.id()
        cnf += [[-acc, -z], [acc, z]]   # z = not acc
        cnf += [[acc, z], [-acc, -z]]
        return ('lit', z)
    return ('lit', acc)

def build(targets, k, chain=False):
    pool = IDPool(); cnf = []
    inp_tt = [[(t >> i) & 1 for t in range(NR)] for i in range(6)]
    # signal values: inputs are constants, gates are variables
    val = [('const', inp_tt[i]) for i in range(6)]
    sa = []; sb = []; outs = []
    for j in range(k):
        navail = 6 + j
        lo = (6 + j - 1) if (chain and j > 0) else 0   # chain: inputs + prev gate only
        A = [pool.id() for _ in range(navail)]; ca = pool.id()
        B = [pool.id() for _ in range(navail)]; cb = pool.id()
        sa.append((A, ca)); sb.append((B, cb))
        cnf.append(A[:])        # each input uses at least one signal
        cnf.append(B[:])
        gv = [pool.id() for _ in range(NR)]
        for t in range(NR):
            def side(sel, c):
                lits = []
                for i in list(range(6)) + list(range(max(6, lo), navail)):
                    kind, v = val[i]
                    if kind == 'const':
                        if v[t]: lits.append(sel[i])
                    else:
                        p = pool.id()
                        cnf.extend([[-p, sel[i]], [-p, v[t]], [p, -sel[i], -v[t]]])
                        lits.append(p)
                return xor_chain(cnf, pool, lits, None)  # const handled below
            la = side(A, ca); lb = side(B, cb)
            def withc(lk, cvar):
                if lk[0] == 'const':
                    z = pool.id()
                    if lk[1] == 0: cnf.extend([[-z, cvar], [z, -cvar]])
                    else: cnf.extend([[-z, -cvar], [z, cvar]])
                    return z
                z = pool.id(); a = lk[1]
                cnf.extend([[-z, a, cvar], [-z, -a, -cvar], [z, -a, cvar], [z, a, -cvar]])
                return z
            za = withc(la, ca); zb = withc(lb, cb)
            g = gv[t]
            cnf += [[-g, za], [-g, zb], [g, -za, -zb]]
        val.append(('var', gv))
    for m, tgt in enumerate(targets):
        nav = len(val); O = [pool.id() for _ in range(nav)]; co = pool.id()
        outs.append((O, co))
        for t in range(NR):
            lits = []
            for i in range(nav):
                kind, v = val[i]
                if kind == 'const':
                    if v[t]: lits.append(O[i])
                else:
                    p = pool.id()
                    cnf.extend([[-p, O[i]], [-p, v[t]], [p, -O[i], -v[t]]])
                    lits.append(p)
            lk = xor_chain(cnf, pool, lits, None)
            if lk[0] == 'const':
                z = pool.id()
                if lk[1] == 0: cnf += [[-z, co], [z, -co]]
                else: cnf += [[-z, -co], [z, co]]
            else:
                z = pool.id(); a = lk[1]
                cnf += [[-z, a, co], [-z, -a, -co], [z, -a, co], [z, a, -co]]
            cnf.append([z] if tgt[t] else [-z])
    return cnf, pool, sa, sb, outs

def solve(targets, k, timeout, want_model=False, chain=False):
    cnf, pool, sa, sb, outs = build(targets, k, chain)
    s = Cadical153(bootstrap_with=cnf)
    t0 = time.time()
    r = s.solve()
    el = time.time() - t0
    wit = None
    if r and want_model:
        mod = set(l for l in s.get_model() if l > 0)
        def dec(sel, c):
            return ([i for i, v in enumerate(sel) if v in mod], c in mod)
        wit = {'k': k,
               'gates': [{'a': dec(*sa[j]), 'b': dec(*sb[j])} for j in range(k)],
               'outs': [dec(*o) for o in outs]}
    s.delete()
    return ('SAT' if r else 'UNSAT'), el, (wit if want_model else len(cnf))

if __name__ == '__main__':
    F = json.load(open(sys.argv[1]))
    # sanity: a function with known small MC
    maj = [1 if ((t & 1) + ((t >> 1) & 1) + ((t >> 2) & 1)) >= 2 else 0 for t in range(NR)]
    r, el, nc = solve([maj], 1, 60)
    print(f'control MAJ3 at k=1: {r} ({el:.1f}s, {nc} clauses)  [expect UNSAT]')
    r, el, nc = solve([maj], 2, 60)
    print(f'control MAJ3 at k=2: {r} ({el:.1f}s, {nc} clauses)  [expect SAT]')
    for side in ('y', 'x'):
        tg = [F[f'{side}{b}'] for b in range(3)]
        print(f'--- {side} side (protected labels)', flush=True)
        for k in range(3, 10):
            r, el, nc = solve(tg, k, 0)
            print(f'   k={k:2d}: {r:6s} ({el:6.1f}s, {nc} clauses)', flush=True)
            if r == 'SAT': break
