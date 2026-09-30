"""Run post190_direct_layers using CaDiCaL/Kissat via PySAT.
"""
import argparse, json, random, time
from pathlib import Path
import z3
from pysat.solvers import Solver
import post190_direct_layers as dl

def solve_sat(samples, layers, gaps, seconds, matching=dl.BEST_ANF, solver_name='cadical300'):
    size = len(samples)
    solver = z3.Solver()
    state = [z3.BitVecVal(sum(((v >> w) & 1) << i for i, v in enumerate(samples)), size)
             for w in range(12)] + [z3.BitVecVal(0, size)] * 6
    target = z3.BitVecVal(sum(int(dl.logo(v & 63, v >> 6)) << i for i, v in enumerate(samples)), size)
    plan = []
    for layer in range(layers):
        if layer:
            for gap in range(gaps):
                idx, on = dl._slots(solver, f'cx{layer}_{gap}', 2, 9)
                state = dl._apply(state, idx, on, 2); plan.append(('cx', idx, on))
        if layer == 0:
            new = state.copy()
            for i, (a, b) in enumerate(matching):
                new[dl.ANCILLAS[i]] = state[dl.ANCILLAS[i]] ^ (state[a] & state[b])
            state = new
            plan.append(('fixed', [(a, b, dl.ANCILLAS[i]) for i, (a, b) in enumerate(matching)], None))
        else:
            idx, on = dl._slots(solver, f'and{layer}', 3, 6)
            state = dl._apply(state, idx, on, 3); plan.append(('and', idx, on))
    solver.add(state[dl.OUT] == target)
    
    # Bit-blast to CNF
    start = time.time()
    goal = z3.Goal()
    goal.add(solver.assertions())
    cnf_tactic = z3.Then(
        z3.With('simplify', blast_distinct=True),
        z3.With('card2bv', keep_cardinality_constraints=False),
        z3.With('bit-blast', blast_full=True),
        'tseitin-cnf'
    )
    cnf = cnf_tactic(goal)[0]
    
    atoms = {}
    clauses = []
    for expr in cnf:
        if z3.is_true(expr): continue
        if z3.is_false(expr): clauses.append([]); continue
        lits = list(expr.children()) if z3.is_or(expr) else [expr]
        clause = []
        for lit in lits:
            neg = z3.is_not(lit)
            atom = lit.arg(0) if neg else lit
            if str(atom) not in atoms:
                atoms[str(atom)] = (len(atoms) + 1, atom)
            var = atoms[str(atom)][0]
            clause.append(-var if neg else var)
        clauses.append(clause)
        
    blast_time = time.time() - start
    print(f'CNF: {len(atoms)} variables, {len(clauses)} clauses (blasted in {blast_time:.2f}s)', flush=True)
    
    # Solve with PySAT
    sat_start = time.time()
    try:
        with Solver(name=solver_name, bootstrap_with=clauses) as s:
            ok = s.solve()
            sol = set(s.get_model() or [])
    except Exception as e:
        print(f'Solver {solver_name} failed: {e}, falling back to cadical195', flush=True)
        with Solver(name='cadical195', bootstrap_with=clauses) as s:
            ok = s.solve()
            sol = set(s.get_model() or [])
            
    sat_time = time.time() - sat_start
    total_time = time.time() - start
    rec = dict(status='sat' if ok else 'unsat', seconds=round(total_time, 2),
               blast_seconds=round(blast_time, 2), sat_seconds=round(sat_time, 2), samples=size)
    if not ok:
        return rec, None
        
    # Reconstruct Z3 model
    recon = z3.Solver()
    recon.add(solver.assertions())
    recon.add([atom == (var in sol) for var, atom in atoms.values()])
    assert recon.check() == z3.sat, 'SAT assignment failed reconstruction'
    m = recon.model()
    
    ops = []
    for kind, idx, on in plan:
        if kind == 'fixed':
            ops.extend([('ccx', list(t)) for t in idx]); continue
        for i, flag in enumerate(on):
            if z3.is_true(m.eval(flag, model_completion=True)):
                ops.append(('ccx' if kind == 'and' else 'cx',
                            [m.eval(v, model_completion=True).as_long() for v in idx[i]]))
    rec['gates'] = len(ops)
    return rec, ops

if __name__ == '__main__':
    for samples_cnt in [8, 16, 24, 32]:
        samples = dl.structural_samples(samples_cnt)
        print(f'\n--- Testing {samples_cnt} samples with L=5, g=3 ---')
        rec, ops = solve_sat(samples, 5, 3, 60, dl.BEST_ANF)
        print(rec)
        if ops:
            bad = dl.evaluate(ops)
            print(f'Gates: {rec.get("gates")}, Counterexamples: {len(bad)}/4096')
