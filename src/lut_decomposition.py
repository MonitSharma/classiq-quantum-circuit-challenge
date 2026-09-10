"""Classical search for mixed-variable 6-LUT decompositions.

For fixed supports, each LUT truth-table entry is a binary MILP variable.  A
positive/negative input pair must differ in at least one LUT output.  The
solver is used only for this classical feasibility stage; no QASM is emitted
until an exact decomposition is found.
"""

import random
from collections import defaultdict
from itertools import permutations, product
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from search import logo, esop


NINPUT = 12
NPOINTS = 1 << NINPUT
POS = np.array([z for z in range(NPOINTS)
                if logo(z & 63, z >> 6)], dtype=np.int32)
NEG = np.array([z for z in range(NPOINTS)
                if not logo(z & 63, z >> 6)], dtype=np.int32)


def projection(z, support):
    out = 0
    for j, bit in enumerate(support):
        out |= ((z >> bit) & 1) << j
    return out


def projections(supports):
    return [np.array([projection(z, s) for z in range(NPOINTS)],
                     dtype=np.int16) for s in supports]


def collisions(values, limit=2000):
    """Return distinct positive/negative pairs sharing a feature code."""
    positive = defaultdict(list)
    negative = defaultdict(list)
    for z in POS:
        code = tuple(int(values[i][z]) for i in range(len(values)))
        positive[code].append(int(z))
    for z in NEG:
        code = tuple(int(values[i][z]) for i in range(len(values)))
        negative[code].append(int(z))
    out = []
    for code in positive.keys() & negative.keys():
        for p in positive[code][:8]:
            for n in negative[code][:8]:
                out.append((p, n))
                if len(out) >= limit:
                    return out
    return out


def solve_supports(supports, initial_pairs=400, rounds=12,
                   collision_batch=2000, time_limit=30, seed=0):
    """Find LUT tables separating marked and unmarked points, if feasible.

    This is a counterexample-guided MILP loop.  It intentionally returns a
    model only after the resulting feature vectors have no positive/negative
    collision across the complete 4096-point domain.
    """
    rng = random.Random(seed)
    proj = projections(supports)
    pairs = set((int(rng.choice(POS)), int(rng.choice(NEG)))
                for _ in range(initial_pairs))
    k = len(supports)
    h_count = 64 * k

    for iteration in range(rounds):
        pair_list = sorted(pairs)
        d_count = len(pair_list) * k
        nvars = h_count + d_count
        rows = (4 * k + 1) * len(pair_list)
        A = lil_matrix((rows, nvars), dtype=float)
        lower = np.full(rows, -np.inf)
        upper = np.full(rows, np.inf)
        row = 0
        for pi, (p, n) in enumerate(pair_list):
            dbase = h_count + pi * k
            for i in range(k):
                hp = i * 64 + int(proj[i][p])
                hn = i * 64 + int(proj[i][n])
                d = dbase + i
                # d >= hp - hn
                A[row, d] = -1
                A[row, hp] = 1
                A[row, hn] = -1
                upper[row] = 0
                row += 1
                # d >= hn - hp
                A[row, d] = -1
                A[row, hp] = -1
                A[row, hn] = 1
                upper[row] = 0
                row += 1
                # d <= hp + hn
                A[row, d] = 1
                A[row, hp] = -1
                A[row, hn] = -1
                upper[row] = 0
                row += 1
                # d <= 2 - hp - hn
                A[row, d] = 1
                A[row, hp] = 1
                A[row, hn] = 1
                upper[row] = 2
                row += 1
            # At least one feature differs.
            for i in range(k):
                A[row, dbase + i] = -1
            upper[row] = -1
            row += 1

        result = milp(
            c=np.zeros(nvars),
            integrality=np.ones(nvars),
            bounds=Bounds(np.zeros(nvars), np.ones(nvars)),
            constraints=LinearConstraint(A.tocsr(), lower, upper),
            options={'time_limit': time_limit},
        )
        if not result.success:
            return None, {'status': result.message, 'iterations': iteration,
                          'pairs': len(pairs)}
        tables = [np.rint(result.x[i * 64:(i + 1) * 64]).astype(np.uint8)
                  for i in range(k)]
        values = [table[proj[i]] for i, table in enumerate(tables)]
        bad = collisions(values, collision_batch)
        print('supports', supports, 'round', iteration,
              'pairs', len(pairs), 'new_collisions', len(bad), flush=True)
        if not bad:
            g = {}
            for z in range(NPOINTS):
                code = sum(int(values[i][z]) << i for i in range(k))
                target = int(z in set(POS))
                if code in g and g[code] != target:
                    raise AssertionError('collision escaped checker')
                g[code] = target
            gmask = sum(v << code for code, v in g.items())
            candidate = canonical_model({
                'tables': [int(sum(int(v) << j for j, v in enumerate(t)))
                           for t in tables],
                'gmask': gmask, 'supports': [list(s) for s in supports],
            })
            return candidate, {
                        'status': 'sat', 'iterations': iteration + 1,
                        'pairs': len(pairs), 'score': model_score(candidate)}
        pairs.update(bad)
    return None, {'status': 'round_limit', 'iterations': rounds,
                  'pairs': len(pairs)}


def solve_supports_z3(supports, initial_pairs=400, rounds=30,
                      collision_batch=4000, time_limit=300, seed=0,
                      verbose=True):
    """Exact CEGAR solver using Z3 Boolean constraints.

    Each marked/unmarked pair contributes one constraint saying that at least
    one LUT output differs.  Only collisions found in a complete model are
    added, so the solver starts small and remains incremental.
    """
    import z3

    rng = random.Random(seed)
    proj = projections(supports)
    k = len(supports)
    solver = z3.Solver()
    solver.set(timeout=int(time_limit * 1000))
    h = [[z3.Bool(f'h_{i}_{j}') for j in range(64)] for i in range(k)]
    pairs = set((int(rng.choice(POS)), int(rng.choice(NEG)))
                for _ in range(initial_pairs))
    pos_set = set(int(z) for z in POS)

    def add_pair(p, n):
        solver.add(z3.Or(*[
            h[i][int(proj[i][p])] != h[i][int(proj[i][n])]
            for i in range(k)
        ]))

    for p, n in pairs:
        add_pair(p, n)
    for iteration in range(rounds):
        status = solver.check()
        if status != z3.sat:
            return None, {'status': str(status), 'iterations': iteration,
                          'pairs': len(pairs)}
        model = solver.model()
        values = [np.array(
            [int(z3.is_true(model.eval(h[i][int(proj[i][z])])) )
             for z in range(NPOINTS)],
            dtype=np.uint8,
        ) for i in range(k)]
        bad = collisions(values, collision_batch)
        if verbose:
            print('z3 supports', supports, 'round', iteration,
                  'pairs', len(pairs), 'new_collisions', len(bad), flush=True)
        if not bad:
            tables = [int(sum(int(z3.is_true(model.eval(h[i][j]))) << j
                              for j in range(64))) for i in range(k)]
            g = {}
            for z in range(NPOINTS):
                code = sum(int(values[i][z]) << i for i in range(k))
                target = int(z in pos_set)
                if code in g and g[code] != target:
                    raise AssertionError('collision escaped Z3 checker')
                g[code] = target
            gmask = sum(v << code for code, v in g.items())
            candidate = canonical_model({
                'tables': tables, 'gmask': gmask,
                'supports': [list(s) for s in supports],
            })
            return candidate, {
                'status': 'sat', 'iterations': iteration + 1,
                'pairs': len(pairs), 'score': model_score(candidate)}
        pairs.update(bad)
        for p, n in bad:
            add_pair(p, n)
    return None, {'status': 'round_limit', 'iterations': rounds,
                  'pairs': len(pairs)}


def solve_supports_z3_direct(supports, time_limit=30):
    """Direct exact Z3 encoding with explicit upper function G.

    This avoids the potentially large positive/negative pair expansion used
    by the CEGAR solver.  For each of the 4096 inputs, a small selector chooses
    one of the 2**k G entries according to the LUT output bits.
    """
    import z3

    k = len(supports)
    proj = projections(supports)
    solver = z3.Solver()
    solver.set(timeout=int(time_limit * 1000))
    h = [[z3.Bool(f'dh_{i}_{j}') for j in range(64)] for i in range(k)]
    g = [z3.Bool(f'dg_{j}') for j in range(1 << k)]
    for z in range(NPOINTS):
        bits = [h[i][int(proj[i][z])] for i in range(k)]
        target = bool(logo(z & 63, z >> 6))
        choices = []
        for code in range(1 << k):
            selector = [bits[i] if code >> i & 1 else z3.Not(bits[i])
                        for i in range(k)]
            choices.append(z3.And(*(selector + [g[code] == target])))
        solver.add(z3.Or(*choices))
    status = solver.check()
    if status != z3.sat:
        return None, {'status': str(status)}
    model = solver.model()
    tables = [int(sum(int(z3.is_true(model.eval(h[i][j]))) << j
                      for j in range(64))) for i in range(k)]
    gmask = int(sum(int(z3.is_true(model.eval(g[j]))) << j
                    for j in range(1 << k)))
    candidate = canonical_model({
        'tables': tables, 'gmask': gmask,
        'supports': [list(s) for s in supports],
    })
    return candidate, {'status': 'sat', 'score': model_score(candidate)}


def solve_joint_z3(k=4, initial_pairs=120, rounds=20,
                   collision_batch=4000, time_limit=10, seed=0,
                   verbose=True):
    """Search support positions and LUT tables in one incremental Z3 model.

    Each feature chooses six strictly increasing bit positions from the 12
    coordinate bits.  The LUT entries and the selected supports are solved
    together against sampled positive/negative pairs; complete-domain
    collisions are then added as counterexamples.  This is the arbitrary-
    support counterpart to :func:`solve_supports_z3`.
    """
    import z3

    rng = random.Random(seed)
    solver = z3.Solver()
    solver.set(timeout=int(time_limit * 1000))
    positions = [[z3.Int(f'jp_{i}_{j}') for j in range(6)]
                 for i in range(k)]
    tables = [[z3.Bool(f'jh_{i}_{j}') for j in range(64)]
              for i in range(k)]
    for row in positions:
        for value in row:
            solver.add(value >= 0, value < NINPUT)
        solver.add(*[row[j] < row[j + 1] for j in range(5)])
    # Feature permutation symmetry: sort the six-bit support rows
    # lexicographically.  This is semantics-preserving because G can relabel
    # its feature inputs, and removes a k! duplication from the joint search.
    for left, right in zip(positions, positions[1:]):
        prefixes_equal = []
        first_less = []
        for slot in range(6):
            prefixes_equal.append(z3.And(*[
                left[p] == right[p] for p in range(slot)
            ]))
            first_less.append(z3.And(
                prefixes_equal[-1], left[slot] < right[slot]
            ))
        solver.add(z3.Or(z3.And(*[
            left[p] == right[p] for p in range(6)
        ]), *first_less))
    # Every input bit is essential to logo, so an exact decomposition must
    # expose every bit in at least one feature support.  This necessary
    # condition removes many degenerate partial-support models early.
    for source_bit in range(NINPUT):
        solver.add(z3.Or(*[
            positions[feature][slot] == source_bit
            for feature in range(k) for slot in range(6)
        ]))

    # Cache symbolic feature values for each endpoint appearing in a pair.
    code_bits = {}
    feature_values = {}

    def feature_value(feature, z):
        key = (feature, z)
        if key in feature_values:
            return feature_values[key]
        bits = []
        for slot in range(6):
            bit = z3.Bool(f'jc_{feature}_{z}_{slot}')
            solver.add(bit == z3.Or(*[
                z3.And(positions[feature][slot] == source_bit,
                       z3.BoolVal(bool((z >> source_bit) & 1)))
                for source_bit in range(NINPUT)
            ]))
            bits.append(bit)
            code_bits[(feature, z, slot)] = bit
        value = z3.Bool(f'jv_{feature}_{z}')
        choices = []
        for table_code in range(64):
            matches = [bits[slot] if (table_code >> slot) & 1
                       else z3.Not(bits[slot]) for slot in range(6)]
            choices.append(z3.And(*(matches + [tables[feature][table_code]])))
        solver.add(value == z3.Or(*choices))
        feature_values[key] = value
        return value

    pairs = set((int(rng.choice(POS)), int(rng.choice(NEG)))
                for _ in range(initial_pairs))
    for positive, negative in pairs:
        solver.add(z3.Or(*[
            feature_value(i, positive) != feature_value(i, negative)
            for i in range(k)
        ]))

    for iteration in range(rounds):
        status = solver.check()
        if status != z3.sat:
            return None, {'status': str(status), 'iterations': iteration,
                          'pairs': len(pairs)}
        model = solver.model()
        support_model = [tuple(model.eval(positions[i][j]).as_long()
                                for j in range(6)) for i in range(k)]
        table_model = [sum(int(z3.is_true(model.eval(tables[i][j]))) << j
                           for j in range(64)) for i in range(k)]
        values = [np.array([
            (table_model[i] >> projection(z, support_model[i])) & 1
            for z in range(NPOINTS)], dtype=np.uint8) for i in range(k)]
        bad = collisions(values, collision_batch)
        if verbose:
            print('joint z3', support_model, 'round', iteration,
                  'pairs', len(pairs), 'new_collisions', len(bad), flush=True)
        if not bad:
            g = {}
            for z in range(NPOINTS):
                code = sum(int(values[i][z]) << i for i in range(k))
                target = int(logo(z & 63, z >> 6))
                if code in g and g[code] != target:
                    raise AssertionError('collision escaped joint checker')
                g[code] = target
            candidate = canonical_model({
                'tables': table_model,
                'gmask': sum(value << code for code, value in g.items()),
                'supports': [list(s) for s in support_model],
            })
            return candidate, {
                'status': 'sat', 'iterations': iteration + 1,
                'pairs': len(pairs), 'score': model_score(candidate),
            }
        pairs.update(bad)
        for positive, negative in bad:
            solver.add(z3.Or(*[
                feature_value(i, positive) != feature_value(i, negative)
                for i in range(k)
            ]))
    return None, {'status': 'round_limit', 'iterations': rounds,
                  'pairs': len(pairs)}


def solve_joint_z3_array(k=4, initial_pairs=120, rounds=30,
                         collision_batch=1000, time_limit=10, seed=0,
                         verbose=True):
    """Joint arbitrary-support search using array-indexed LUT truth tables.

    This has the same semantics as :func:`solve_joint_z3`, but represents a
    LUT as a Z3 array and uses ``Select(table, code)`` instead of expanding a
    64-way selector for every endpoint.  It is intended for larger CEGAR
    batches; the returned model is still converted to ordinary integer
    truth-table masks before scoring or emission.
    """
    import z3

    rng = random.Random(seed)
    solver = z3.Solver()
    solver.set(timeout=int(time_limit * 1000))
    positions = [[z3.Int(f'ap_{i}_{j}') for j in range(6)]
                 for i in range(k)]
    tables = [z3.Array(f'at_{i}', z3.IntSort(), z3.BoolSort())
              for i in range(k)]
    for row in positions:
        for value in row:
            solver.add(value >= 0, value < NINPUT)
        solver.add(*[row[j] < row[j + 1] for j in range(5)])
    for left, right in zip(positions, positions[1:]):
        first_less = []
        for slot in range(6):
            prefix = [left[p] == right[p] for p in range(slot)]
            first_less.append(z3.And(*(prefix + [left[slot] < right[slot]])))
        solver.add(z3.Or(z3.And(*[
            left[p] == right[p] for p in range(6)
        ]), *first_less))
    for source_bit in range(NINPUT):
        solver.add(z3.Or(*[
            positions[feature][slot] == source_bit
            for feature in range(k) for slot in range(6)
        ]))

    feature_values = {}

    def feature_value(feature, z):
        key = (feature, z)
        if key not in feature_values:
            code = z3.Sum(*[
                z3.If(positions[feature][slot] == source_bit,
                      ((z >> source_bit) & 1) << slot, 0)
                for slot in range(6) for source_bit in range(NINPUT)
            ])
            feature_values[key] = z3.Select(tables[feature], code)
        return feature_values[key]

    pairs = set((int(rng.choice(POS)), int(rng.choice(NEG)))
                for _ in range(initial_pairs))
    for positive, negative in pairs:
        solver.add(z3.Or(*[
            feature_value(i, positive) != feature_value(i, negative)
            for i in range(k)
        ]))

    for iteration in range(rounds):
        status = solver.check()
        if status != z3.sat:
            return None, {'status': str(status), 'iterations': iteration,
                          'pairs': len(pairs)}
        model = solver.model()
        support_model = [tuple(model.eval(positions[i][j]).as_long()
                                for j in range(6)) for i in range(k)]
        table_model = []
        for i in range(k):
            table_model.append(sum(
                int(z3.is_true(model.eval(z3.Select(tables[i], code),
                                            model_completion=True))) << code
                for code in range(64)
            ))
        values = [np.array([
            (table_model[i] >> projection(z, support_model[i])) & 1
            for z in range(NPOINTS)], dtype=np.uint8) for i in range(k)]
        bad = collisions(values, collision_batch)
        if verbose:
            print('joint array z3', support_model, 'round', iteration,
                  'pairs', len(pairs), 'new_collisions', len(bad), flush=True)
        if not bad:
            g = {}
            for z in range(NPOINTS):
                code = sum(int(values[i][z]) << i for i in range(k))
                target = int(logo(z & 63, z >> 6))
                if code in g and g[code] != target:
                    raise AssertionError('collision escaped array checker')
                g[code] = target
            candidate = canonical_model({
                'tables': table_model,
                'gmask': sum(value << code for code, value in g.items()),
                'supports': [list(s) for s in support_model],
            })
            return candidate, {
                'status': 'sat', 'iterations': iteration + 1,
                'pairs': len(pairs), 'score': model_score(candidate),
            }
        pairs.update(bad)
        for positive, negative in bad:
            solver.add(z3.Or(*[
                feature_value(i, positive) != feature_value(i, negative)
                for i in range(k)
            ]))
    return None, {'status': 'round_limit', 'iterations': rounds,
                  'pairs': len(pairs)}


def solve_joint_z3_bool(k=4, initial_pairs=120, rounds=30,
                        collision_batch=1000, time_limit=10, seed=0,
                        verbose=True):
    """Joint arbitrary-support search using a pure Boolean SAT encoding."""
    import z3

    rng = random.Random(seed)
    solver = z3.Solver()
    solver.set(timeout=int(time_limit * 1000))
    selected = [[[z3.Bool(f'bsel_{i}_{slot}_{bit}')
                  for bit in range(NINPUT)] for slot in range(6)]
                for i in range(k)]
    tables = [[z3.Bool(f'btab_{i}_{code}') for code in range(64)]
              for i in range(k)]
    for feature in range(k):
        for slot in range(6):
            row = selected[feature][slot]
            solver.add(z3.PbEq([(value, 1) for value in row], 1))
        for slot in range(5):
            # Enforce strictly increasing support positions using one-hot
            # implications, avoiding integer arithmetic entirely.
            for left in range(NINPUT):
                for right in range(left + 1):
                    solver.add(z3.Or(z3.Not(selected[feature][slot][left]),
                                     z3.Not(selected[feature][slot + 1][right])))
    # Remove feature-permutation symmetry using lexicographic support order.
    # With one-hot rows, equality/less-than are small Boolean disjunctions.
    for left_feature in range(k - 1):
        right_feature = left_feature + 1
        equal_slots = []
        less_slots = []
        for slot in range(6):
            left_row = selected[left_feature][slot]
            right_row = selected[right_feature][slot]
            equal_slots.append(z3.Or(*[
                z3.And(left_row[bit], right_row[bit])
                for bit in range(NINPUT)
            ]))
            less_slots.append(z3.Or(*[
                z3.And(left_row[a], right_row[b])
                for a in range(NINPUT) for b in range(a + 1, NINPUT)
            ]))
        first_less = [z3.And(*(equal_slots[:slot] + [less_slots[slot]]))
                     for slot in range(6)]
        solver.add(z3.Or(z3.And(*equal_slots), *first_less))
    for source_bit in range(NINPUT):
        solver.add(z3.Or(*[
            selected[feature][slot][source_bit]
            for feature in range(k) for slot in range(6)
        ]))

    code_bits = {}
    feature_values = {}

    def feature_value(feature, z):
        key = (feature, z)
        if key in feature_values:
            return feature_values[key]
        bits = []
        for slot in range(6):
            bit = z3.Bool(f'bcode_{feature}_{z}_{slot}')
            solver.add(bit == z3.Or(*[
                selected[feature][slot][source_bit]
                for source_bit in range(NINPUT)
                if (z >> source_bit) & 1
            ]))
            bits.append(bit)
            code_bits[(feature, z, slot)] = bit
        value = z3.Bool(f'bvalue_{feature}_{z}')
        choices = []
        for code in range(64):
            matches = [bits[slot] if (code >> slot) & 1
                       else z3.Not(bits[slot]) for slot in range(6)]
            choices.append(z3.And(*(matches + [tables[feature][code]])))
        solver.add(value == z3.Or(*choices))
        feature_values[key] = value
        return value

    pairs = set((int(rng.choice(POS)), int(rng.choice(NEG)))
                for _ in range(initial_pairs))
    for positive, negative in pairs:
        solver.add(z3.Or(*[
            feature_value(i, positive) != feature_value(i, negative)
            for i in range(k)
        ]))

    for iteration in range(rounds):
        status = solver.check()
        if status != z3.sat:
            return None, {'status': str(status), 'iterations': iteration,
                          'pairs': len(pairs)}
        model = solver.model()
        support_model = []
        for feature in range(k):
            support_model.append(tuple(
                bit for slot in range(6)
                for bit in range(NINPUT)
                if z3.is_true(model.eval(selected[feature][slot][bit]))
            ))
        table_model = [sum(
            int(z3.is_true(model.eval(tables[i][code]))) << code
            for code in range(64)) for i in range(k)]
        values = [np.array([
            (table_model[i] >> projection(z, support_model[i])) & 1
            for z in range(NPOINTS)], dtype=np.uint8) for i in range(k)]
        bad = collisions(values, collision_batch)
        if verbose:
            print('joint bool z3', support_model, 'round', iteration,
                  'pairs', len(pairs), 'new_collisions', len(bad), flush=True)
        if not bad:
            g = {}
            for z in range(NPOINTS):
                code = sum(int(values[i][z]) << i for i in range(k))
                target = int(logo(z & 63, z >> 6))
                if code in g and g[code] != target:
                    raise AssertionError('collision escaped Boolean checker')
                g[code] = target
            candidate = canonical_model({
                'tables': table_model,
                'gmask': sum(value << code for code, value in g.items()),
                'supports': [list(s) for s in support_model],
            })
            return candidate, {
                'status': 'sat', 'iterations': iteration + 1,
                'pairs': len(pairs), 'score': model_score(candidate),
            }
        pairs.update(bad)
        for positive, negative in bad:
            solver.add(z3.Or(*[
                feature_value(i, positive) != feature_value(i, negative)
                for i in range(k)
            ]))
    return None, {'status': 'round_limit', 'iterations': rounds,
                  'pairs': len(pairs)}


def solve_joint_pysat(k=4, initial_pairs=120, rounds=100,
                      collision_batch=100, seed=0, verbose=True,
                      conflict_budget=None):
    """Joint arbitrary-support search using an incremental native SAT solver.

    Unlike the Z3 variants, a complete Boolean CNF solver always returns SAT
    or UNSAT for each finite CEGAR state.  Support positions, LUT entries,
    endpoint code bits, and endpoint feature values are all Booleanized with
    Tseitin clauses.  The full 4096-point collision check remains outside the
    SAT core and contributes the next exact counterexample batch.
    """
    from pysat.solvers import Solver

    rng = random.Random(seed)
    next_var = 0

    def new_var():
        nonlocal next_var
        next_var += 1
        return next_var

    clauses = []
    selected = [[[new_var() for _ in range(NINPUT)] for _ in range(6)]
                for _ in range(k)]
    tables = [[new_var() for _ in range(64)] for _ in range(k)]

    def add(clause):
        clauses.append([int(x) for x in clause])

    # Exactly one bit index per support slot, with strictly increasing slots.
    for feature in range(k):
        for slot in range(6):
            row = selected[feature][slot]
            add(row)
            for i in range(NINPUT):
                for j in range(i + 1, NINPUT):
                    add((-row[i], -row[j]))
            if slot:
                previous = selected[feature][slot - 1]
                for left in range(NINPUT):
                    for right in range(left + 1):
                        add((-previous[left], -row[right]))
    # Every input bit is essential and must occur in at least one support.
    for source_bit in range(NINPUT):
        add([selected[feature][slot][source_bit]
             for feature in range(k) for slot in range(6)])

    def and_var(left, right):
        value = new_var()
        add([-value, left])
        add([-value, right])
        add([value, -left, -right])
        return value

    def or_var(literals):
        value = new_var()
        literals = list(literals)
        add([-value] + literals)
        for literal in literals:
            add([-literal, value])
        return value

    # Lexicographically order feature rows, removing k! equivalent copies.
    for left_feature in range(k - 1):
        right_feature = left_feature + 1
        prefix = None
        first_less = []
        for slot in range(6):
            left_row = selected[left_feature][slot]
            right_row = selected[right_feature][slot]
            equal_pairs = [and_var(left_row[bit], right_row[bit])
                           for bit in range(NINPUT)]
            less_pairs = [and_var(left_row[a], right_row[b])
                          for a in range(NINPUT)
                          for b in range(a + 1, NINPUT)]
            equal = or_var(equal_pairs)
            less = or_var(less_pairs)
            first_less.append(less if prefix is None
                             else and_var(prefix, less))
            prefix = equal if prefix is None else and_var(prefix, equal)
        add(first_less + [prefix])

    endpoint_bits = {}
    endpoint_values = {}

    def endpoint_value(feature, z):
        key = (feature, z)
        if key in endpoint_values:
            return endpoint_values[key]
        bits = []
        for slot in range(6):
            bit = new_var()
            bits.append(bit)
            active = [selected[feature][slot][source_bit]
                      for source_bit in range(NINPUT)
                      if (z >> source_bit) & 1]
            if active:
                add([-bit] + active)
                for literal in active:
                    add([-literal, bit])
            else:
                add([-bit])
            endpoint_bits[(feature, z, slot)] = bit

        matches = []
        terms = []
        for code in range(64):
            match = new_var()
            matches.append(match)
            literals = [bits[slot] if (code >> slot) & 1
                        else -bits[slot] for slot in range(6)]
            for literal in literals:
                add([-match, literal])
            add([match] + [-literal for literal in literals])
            term = new_var()
            terms.append(term)
            table = tables[feature][code]
            add([-term, match])
            add([-term, table])
            add([term, -match, -table])
        value = new_var()
        for term in terms:
            add([-term, value])
        add([-value] + terms)
        endpoint_values[key] = value
        return value

    def pair_clauses(positive, negative):
        values = [(endpoint_value(i, positive), endpoint_value(i, negative))
                  for i in range(k)]
        # At least one feature output differs. Introduce one exact XOR
        # variable per feature pair and require their disjunction.
        diffs = []
        for left, right in values:
            diff = new_var()
            add([-diff, left, right])
            add([-diff, -left, -right])
            add([diff, -left, right])
            add([diff, left, -right])
            diffs.append(diff)
        add(diffs)

    pairs = set((int(rng.choice(POS)), int(rng.choice(NEG)))
                for _ in range(initial_pairs))
    for positive, negative in pairs:
        pair_clauses(positive, negative)

    clause_index = len(clauses)
    with Solver(name='glucose4', bootstrap_with=clauses) as solver:
        for iteration in range(rounds):
            if conflict_budget is None:
                status = solver.solve()
            else:
                solver.conf_budget(int(conflict_budget))
                status = solver.solve_limited()
                if status is None:
                    return None, {'status': 'unknown',
                                  'iterations': iteration,
                                  'pairs': len(pairs)}
            if not status:
                return None, {'status': 'unsat', 'iterations': iteration,
                              'pairs': len(pairs)}
            assignment = set(literal for literal in solver.get_model()
                             if literal > 0)
            support_model = [tuple(
                bit for slot in range(6)
                for bit in range(NINPUT)
                if selected[feature][slot][bit] in assignment
            ) for feature in range(k)]
            table_model = [sum(
                int(tables[i][code] in assignment) << code
                for code in range(64)) for i in range(k)]
            projected = projections(support_model)
            values = [np.asarray(
                np.right_shift(np.uint64(table_model[i]),
                               projected[i].astype(np.uint64)) & 1,
                dtype=np.uint8) for i in range(k)]
            bad = collisions(values, collision_batch)
            if verbose:
                print('joint pysat', support_model, 'round', iteration,
                      'pairs', len(pairs), 'new_collisions', len(bad),
                      flush=True)
            if not bad:
                g = {}
                for z in range(NPOINTS):
                    code = sum(int(values[i][z]) << i for i in range(k))
                    target = int(logo(z & 63, z >> 6))
                    if code in g and g[code] != target:
                        raise AssertionError('collision escaped PySAT checker')
                    g[code] = target
                candidate = canonical_model({
                    'tables': table_model,
                    'gmask': sum(value << code for code, value in g.items()),
                    'supports': [list(s) for s in support_model],
                })
                return candidate, {
                    'status': 'sat', 'iterations': iteration + 1,
                    'pairs': len(pairs), 'score': model_score(candidate),
                }
            pairs.update(bad)
            for positive, negative in bad:
                pair_clauses(positive, negative)
            # Add only clauses generated since the last solver call.
            for clause in clauses[clause_index:]:
                solver.add_clause(clause)
            clause_index = len(clauses)
    return None, {'status': 'round_limit', 'iterations': rounds,
                  'pairs': len(pairs)}


def solve_joint_pysat_direct(k=4, conflict_budget=None, verbose=True):
    """Solve the unrestricted-support decomposition over all 4096 inputs.

    This is the non-CEGAR formulation.  Each LUT is represented by a
    six-level Boolean mux tree, and an explicit 2**k upper table G is tied to
    every input's feature code.  A returned UNSAT is therefore a global proof
    for that feature count, subject only to the SAT solver's exact result.
    """
    from pysat.solvers import Solver

    next_var = 0

    def new_var():
        nonlocal next_var
        next_var += 1
        return next_var

    clauses = []

    def add(clause):
        clauses.append([int(x) for x in clause])

    selected = [[[new_var() for _ in range(NINPUT)] for _ in range(6)]
                for _ in range(k)]
    tables = [[new_var() for _ in range(64)] for _ in range(k)]
    gtable = [new_var() for _ in range(1 << k)]

    for feature in range(k):
        for slot in range(6):
            row = selected[feature][slot]
            add(row)
            for i in range(NINPUT):
                for j in range(i + 1, NINPUT):
                    add((-row[i], -row[j]))
            if slot:
                previous = selected[feature][slot - 1]
                for left in range(NINPUT):
                    for right in range(left + 1):
                        add((-previous[left], -row[right]))
    for source_bit in range(NINPUT):
        add([selected[feature][slot][source_bit]
             for feature in range(k) for slot in range(6)])

    def and_var(left, right):
        value = new_var()
        add((-value, left)); add((-value, right))
        add((value, -left, -right))
        return value

    def or_var(literals):
        value = new_var(); literals = list(literals)
        add([-value] + literals)
        for literal in literals:
            add((-literal, value))
        return value

    # Feature permutation symmetry.
    for left_feature in range(k - 1):
        right_feature = left_feature + 1
        prefix = None; first_less = []
        for slot in range(6):
            left_row = selected[left_feature][slot]
            right_row = selected[right_feature][slot]
            equal = or_var([and_var(left_row[bit], right_row[bit])
                            for bit in range(NINPUT)])
            less = or_var([and_var(left_row[a], right_row[b])
                           for a in range(NINPUT)
                           for b in range(a + 1, NINPUT)])
            first_less.append(less if prefix is None
                             else and_var(prefix, less))
            prefix = equal if prefix is None else and_var(prefix, equal)
        add(first_less + [prefix])

    def mux_var(control, low, high):
        """Return m = low when control=0, high when control=1."""
        value = new_var()
        add((-control, -low, value))
        add((-control, low, -value))
        add((control, -high, value))
        add((control, high, -value))
        return value

    roots = []
    for z in range(NPOINTS):
        feature_roots = []
        for feature in range(k):
            code = []
            for slot in range(6):
                bit = new_var()
                active = [selected[feature][slot][source_bit]
                          for source_bit in range(NINPUT)
                          if (z >> source_bit) & 1]
                if active:
                    add([-bit] + active)
                    for literal in active:
                        add((-literal, bit))
                else:
                    add((-bit,))
                code.append(bit)
            level = list(tables[feature])
            for bit_position in range(6):
                level = [mux_var(code[bit_position], level[index],
                                 level[index + 1])
                         for index in range(0, len(level), 2)]
            feature_roots.append(level[0])
        roots.append(feature_roots)

        for upper_code in range(1 << k):
            match = new_var()
            literals = [feature_roots[i] if (upper_code >> i) & 1
                        else -feature_roots[i] for i in range(k)]
            for literal in literals:
                add((-match, literal))
            add([match] + [-literal for literal in literals])
            target = bool(logo(z & 63, z >> 6))
            add((-match, gtable[upper_code] if target
                 else -gtable[upper_code]))

        if verbose and z and z % 512 == 0:
            print('direct SAT encoded', z, 'inputs', 'vars', next_var,
                  'clauses', len(clauses), flush=True)

    if verbose:
        print('direct SAT solve', 'vars', next_var,
              'clauses', len(clauses), flush=True)
    with Solver(name='glucose4', bootstrap_with=clauses) as solver:
        if conflict_budget is None:
            status = solver.solve()
        else:
            solver.conf_budget(int(conflict_budget))
            status = solver.solve_limited()
        if status is None:
            return None, {'status': 'unknown', 'variables': next_var,
                          'clauses': len(clauses)}
        if not status:
            return None, {'status': 'unsat', 'variables': next_var,
                          'clauses': len(clauses)}
        assignment = set(literal for literal in solver.get_model()
                         if literal > 0)
    support_model = [tuple(
        bit for slot in range(6)
        for bit in range(NINPUT)
        if selected[feature][slot][bit] in assignment
    ) for feature in range(k)]
    table_model = [sum(int(tables[i][code] in assignment) << code
                       for code in range(64)) for i in range(k)]
    gmask = sum(int(gtable[code] in assignment) << code
                for code in range(1 << k))
    candidate = canonical_model({
        'tables': table_model, 'gmask': gmask,
        'supports': [list(s) for s in support_model],
    })
    return candidate, {'status': 'sat', 'score': model_score(candidate),
                       'variables': next_var, 'clauses': len(clauses)}


def random_supports(k=4, seed=0):
    rng = random.Random(seed)
    universe = list(range(NINPUT))
    return tuple(tuple(sorted(rng.sample(universe, 6))) for _ in range(k))


def canonical_model(model):
    """Return a representative under feature permutation/complement symmetry.

    Reordering features and complementing an individual LUT output does not
    change the represented predicate: the upper function can be relabeled
    accordingly.  Canonicalizing these equivalent encodings keeps later
    support/codebook comparisons from counting the same decomposition many
    times.  This is intentionally small (at most 5! * 2**5 cases) because it
    is used only after a satisfying model has been found.
    """
    supports = [tuple(s) for s in model['supports']]
    tables = [int(t) for t in model['tables']]
    k = len(supports)
    gmask = int(model['gmask'])
    best = None
    for order in permutations(range(k)):
        for flips in product((0, 1), repeat=k):
            new_supports = tuple(supports[i] for i in order)
            new_tables = tuple(
                tables[i] ^ ((1 << 64) - 1) if flips[j] else tables[i]
                for j, i in enumerate(order)
            )
            new_gmask = 0
            for old_code in range(1 << k):
                new_code = sum(
                    (((old_code >> order[j]) & 1) ^ flips[j]) << j
                    for j in range(k)
                )
                if (gmask >> old_code) & 1:
                    new_gmask |= 1 << new_code
            key = (new_supports, new_tables, new_gmask)
            if best is None or key < best[0]:
                best = (key, {
                    'supports': [list(s) for s in new_supports],
                    'tables': list(new_tables),
                    'gmask': new_gmask,
                })
    return best[1]


def model_score(model):
    """Return the comparison key for an exact decomposition model.

    The upper ESOP term count is the main central-function cost.  LUT count,
    support width, and total LUT truth-table Hamming weight provide stable
    tie-breakers for quantum-emitter cost without pretending they equal the
    final transpiled depth.
    """
    canonical = canonical_model(model)
    k = len(canonical['tables'])
    g_terms = len(esop(canonical['gmask'], k))
    lut_weight = sum(int(t).bit_count() for t in canonical['tables'])
    return (g_terms, k, sum(len(s) for s in canonical['supports']), lut_weight)


if __name__ == '__main__':
    supports = random_supports(4, 0)
    model, info = solve_supports_z3_direct(supports)
    print('result', model, info, flush=True)
