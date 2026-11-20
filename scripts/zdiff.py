"""2-D finite-difference field solver: edge-coupled microstrip, odd mode -> Zdiff = 2*Zodd.
usage: zdiff.py w s [h=0.2104] [er=4.4] [t=0.035] [--mask]  (mm). Ground plane below the dielectric, air above.
--mask adds LPI soldermask as JLCPCB specifies it for impedance work: 1.2 mil (0.0305 mm) on laminate and between
traces, 0.6 mil (0.015 mm) on copper tops and sides, er 3.8."""
import sys, numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
MASK = '--mask' in sys.argv; sys.argv = [a for a in sys.argv if a != '--mask']
MK_LAM, MK_CU, MK_ER = 0.0305, 0.015, 3.8
w, s = float(sys.argv[1]), float(sys.argv[2])
h = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2104
er = float(sys.argv[4]) if len(sys.argv) > 4 else 4.4
t = float(sys.argv[5]) if len(sys.argv) > 5 else 0.035
d = 0.005; W = 2 * w + s + 8 * h + 2.0; H = h + t + 10 * h
nx, ny = int(W / d), int(H / d)
x = (np.arange(nx) + 0.5) * d - W / 2; y = (np.arange(ny) + 0.5) * d
def solve(eps_on):
    eps = np.ones((ny, nx)); 
    if eps_on:
        eps[y < h, :] = er
        if MASK:
            Y, X = y[:, None] + 0 * x[None, :], x[None, :] + 0 * y[:, None]
            on_lam = (Y >= h) & (Y < h + MK_LAM)
            near = np.zeros_like(Y, bool)
            for cx0, cx1 in ((-s / 2 - w, -s / 2), (s / 2, s / 2 + w)):
                near |= (X >= cx0 - MK_CU) & (X <= cx1 + MK_CU) & (Y >= h) & (Y <= h + t + MK_CU)
            eps[on_lam | near] = MK_ER
    V = np.full((ny, nx), np.nan)
    tr = (y[:, None] >= h) & (y[:, None] <= h + t)
    c1 = (x[None, :] >= -s / 2 - w) & (x[None, :] <= -s / 2)
    c2 = (x[None, :] >= s / 2) & (x[None, :] <= s / 2 + w)
    V[tr & c1] = 1.0; V[tr & c2] = -1.0
    fixed = ~np.isnan(V)
    idx = -np.ones((ny, nx), int); free = ~fixed; idx[free] = np.arange(free.sum())
    rows, cols, vals = [], [], []; b = np.zeros(free.sum())
    for (dj, di) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        J, I = np.nonzero(free)
        Jn, In = J + dj, I + di
        inside = (Jn >= 0) & (Jn < ny) & (In >= 0) & (In < nx)
        # boundary: ground at bottom (j<0) -> V=0 Dirichlet; others: V=0 far away (top/sides)
        e = np.where(inside, 0.5 * (eps[J, I] + eps[np.clip(Jn, 0, ny - 1), np.clip(In, 0, nx - 1)]), eps[J, I])
        k = idx[J, I]
        rows += list(k); cols += list(k); vals += list(-e)
        m = inside.copy(); m[inside] = free[Jn[inside], In[inside]]
        rows += list(k[m]); cols += list(idx[Jn[m], In[m]]); vals += list(e[m])
        mf = inside.copy(); mf[inside] = fixed[Jn[inside], In[inside]]
        np.add.at(b, k[mf], -e[mf] * V[Jn[mf], In[mf]])
    A = sp.csr_matrix((vals, (rows, cols)), shape=(free.sum(), free.sum()))
    sol = spl.spsolve(A, b); V[free] = sol
    # charge on conductor 1 = sum of eps*(V1 - Vneighbor) over its boundary (Gauss), per unit length * eps0
    Q = 0.0
    J, I = np.nonzero(tr & c1)
    for (dj, di) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        Jn, In = J + dj, I + di
        ok = (Jn >= 0) & (Jn < ny) & (In >= 0) & (In < nx)
        Jn, In, Jo, Io = Jn[ok], In[ok], J[ok], I[ok]
        m = ~(tr & c1)[Jn, In]
        e = 0.5 * (eps[Jo[m], Io[m]] + eps[Jn[m], In[m]])
        Q += np.sum(e * (V[Jo[m], Io[m]] - V[Jn[m], In[m]]))
    return Q * 8.854e-12          # C per metre for 1 V on conductor 1 (odd mode)
C = solve(True); C0 = solve(False)
c = 2.998e8
Zodd = 1.0 / (c * np.sqrt(C * C0)); eeff = C / C0
print(f"w={w} s={s} h={h} er={er} t={t}{' +mask' if MASK else ''}: Zodd={Zodd:.1f}  Zdiff={2*Zodd:.1f} ohm  eeff={eeff:.2f}")
