"""fastfit.py : analytic-gradient instantiation of CX templates with parametrized 1q slots (n/z/x/u)."""
import numpy as np
from scipy.optimize import minimize, least_squares
NP = {'n': 0, 'z': 1, 'x': 1, 'u': 3}

def m_and_d(kind, p):
    if kind == 'z':
        a = p[0]; e = np.exp(-0.5j * a); f = np.exp(0.5j * a)
        return np.diag([e, f]), [np.diag([-0.5j * e, 0.5j * f])]
    if kind == 'x':
        a = p[0]; c = np.cos(a / 2); s = np.sin(a / 2)
        return np.array([[c, -1j * s], [-1j * s, c]]), [np.array([[-s / 2, -0.5j * c], [-0.5j * c, -s / 2]])]
    t, ph, la = p; c = np.cos(t / 2); s = np.sin(t / 2); el = np.exp(1j * la); ep = np.exp(1j * ph); epl = ep * el
    M = np.array([[c, -el * s], [ep * s, epl * c]])
    dt = np.array([[-s / 2, -el * c / 2], [ep * c / 2, -epl * s / 2]])
    dp = np.array([[0, 0], [1j * ep * s, 1j * epl * c]])
    dl = np.array([[0, -1j * el * s], [0, 1j * epl * c]])
    return M, [dt, dp, dl]

def emb(m, q, k): return np.kron(np.kron(np.eye(1 << q), m), np.eye(1 << (k - 1 - q)))

def cxmat(c, t, k):
    D = 1 << k; M = np.zeros((D, D))
    for s in range(D):
        b = s ^ ((1 << (k - 1 - t)) if (s >> (k - 1 - c)) & 1 else 0); M[b, s] = 1
    return M

class Template:
    def __init__(self, seq, kinds, k):
        self.seq, self.kinds, self.k = seq, kinds, k
        self.slots = [(q, kinds[q]) for q in range(k)]
        self.items = [('s', 0), ('s', 1), ('s', 2)][:0]
        items = [('s', q) for q in range(k)]; si = k
        for c, t in seq:
            items.append(('c', cxmat(c, t, k)))
            for q in (c, t):
                self.slots.append((q, kinds[si])); items.append(('s', si)); si += 1
        self.items = [(typ, v) for typ, v in items]
        self.npar = sum(NP[kd] for _, kd in self.slots)

    def mats(self, p):
        k = self.k; out = []; j = 0
        for typ, v in self.items:
            if typ == 'c': out.append((v, None)); continue
            q, kd = self.slots[v]
            if kd == 'n': continue
            M, dM = m_and_d(kd, p[j:j + NP[kd]]); j += NP[kd]
            out.append((emb(M, q, k), [emb(d, q, k) for d in dM]))
        return out

    def V(self, p):
        V = np.eye(1 << self.k, dtype=complex)
        for M, _ in self.mats(p): V = M @ V
        return V

    def cost_grad(self, p, Ud):   # Ud = U^dagger ; z = tr(Ud V)
        ms = self.mats(p); n = len(ms); D = 1 << self.k
        pre = [np.eye(D, dtype=complex)]
        for M, _ in ms: pre.append(M @ pre[-1])
        z = np.trace(Ud @ pre[-1]); az = abs(z) + 1e-300
        g = []; suf = Ud.copy()          # suf = Ud @ (product of gates after position i)
        grads = [None] * n
        for i in range(n - 1, -1, -1):
            M, dMs = ms[i]
            if dMs is not None:
                # dz = tr(suf @ dM @ pre[i])
                A = pre[i] @ suf
                grads[i] = [np.sum(dM.T * A) for dM in dMs]   # tr(dM @ A) = sum(dM.T * A)
            suf = suf @ M
        for gi in grads:
            if gi is not None: g += gi
        g = np.array(g)
        f = 1 - az / D
        df = -np.real(np.conj(z) * g) / (az * D)
        return f, df

def fit(U, seq, kinds, k, starts=4, rng=None, tol=1e-13):
    rng = rng if rng is not None else np.random.default_rng(0)
    T = Template(seq, kinds, k); Ud = U.conj().T; D = 1 << k
    if T.npar == 0:
        V = T.V([]); z = np.trace(Ud @ V)
        return (np.array([]), 0.0) if abs(abs(z) - D) < 1e-11 and np.max(abs(V - z / abs(z) * U)) < 1e-12 else (None, None)
    for _ in range(starts):
        r = minimize(T.cost_grad, rng.uniform(0, 2 * np.pi, T.npar), args=(Ud,), jac=True, method='L-BFGS-B',
                     options=dict(maxiter=4000, ftol=1e-16, gtol=1e-12))
        if r.fun < 1e-8:
            p0 = np.append(r.x, np.angle(np.trace(Ud @ T.V(r.x))))
            def res(q):
                Dm = T.V(q[:-1]) - np.exp(1j * q[-1]) * U
                return np.concatenate([Dm.real.ravel(), Dm.imag.ravel()])
            ls = least_squares(res, p0, xtol=1e-15, ftol=1e-15, gtol=1e-15, method='lm')
            err = np.max(abs(T.V(ls.x[:-1]) - np.exp(1j * ls.x[-1]) * U))
            if err < tol: return ls.x[:-1], err
    return None, None
