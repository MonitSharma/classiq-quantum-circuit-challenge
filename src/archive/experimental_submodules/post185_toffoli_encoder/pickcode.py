"""Given x/y encoder specs (annealer JSON), enumerate separating codes on both sides and pick the
pair minimizing kernel mask count (integer ANF lift)."""
import sys, json, subprocess, itertools, random
from buildenc import classical
from kernelcost import anf_solution, kernel_masks

def seps(spec, side):
    w = classical(spec)
    inp = ' '.join(format(t, 'x') for t in w)
    out = subprocess.run(['sa/codes', side], input=inp, capture_output=True, text=True).stdout
    rows = [tuple(map(int, l.split())) for l in out.strip().splitlines()]
    return w, rows

def codevals(w, rows):
    return [sum(((bin(r & sum(((w[j] >> x) & 1) << j for j in range(9))).count('1')) & 1) << i for i, r in enumerate(rows)) for x in range(64)]

if __name__ == '__main__':
    xs = json.load(open(sys.argv[1])); ys = json.load(open(sys.argv[2]))
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    wx, rx = seps(xs, 'x'); wy, ry = seps(ys, 'y')
    print('separating codes: x', len(rx), 'y', len(ry), flush=True)
    rng = random.Random(0)
    pairs = [(a, b) for a in rx for b in ry]
    rng.shuffle(pairs)
    best = None
    for a, b in pairs[:budget]:
        t = anf_solution(codevals(wy, b), codevals(wx, a))
        if t is None: continue
        m = kernel_masks(t)
        if best is None or m < best[0]:
            best = (m, a, b); print('masks', m, a, b, flush=True)
    xs['G'] = list(best[1]); ys['G'] = list(best[2])
    json.dump(xs, open(sys.argv[1].replace('.json', '_best.json'), 'w'))
    json.dump(ys, open(sys.argv[2].replace('.json', '_best.json'), 'w'))
