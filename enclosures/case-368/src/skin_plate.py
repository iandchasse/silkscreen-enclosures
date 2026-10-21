"""Light strip: the channel's skin under a fingertip, as a Kirchhoff plate (mechanics.channel_skin).

The plate is the skin over the bar's channel: X from the side wall's face in the channel (STRIP_RIBS['x0'], -1.42) to
where the window's 45-degree bevel meets the channel's ceiling (X 2.03), Y over the channel (CHANNEL_Y). It is
CHANNEL_SKIN thick up to where the bevel reaches the face (X 1.63) and tapers to nothing at 2.03. Supports:
  wall       clamped along the side wall (the skin runs into the 2.7 mm wall and the front edge's round)
  ends       clamped at both ends of the channel: the skin there is 1.4 (over the foot's pocket) and 1.8 (the
             frame above the fold zone) thick
  pads       w = 0 where each hold-down pad meets the skin (X 1.70..2.03, PAD_LEN long): the pads bear on the
             panel's PS film, which the midplate springs hold up against them (the pads carry < 0.2 N here, well
             inside the springs' preload, so the panel does not move)
  pad ribs   (PAD_RIBS, 2026-09-26) the skin is CHANNEL_SKIN + the rib's depth thick from the wall to the pad over
             each rib's Y span (the rib's offset below the skin's mid-plane is not modelled, which makes it softer)
The bar's stop ribs and the wall are not modelled as stiffening, and the load is all on the skin, none on the side
wall beside it: both make the answer high. Element: the ACM (Adini-Clough-Melosh) 12-dof rectangle, 4 x 4 Gauss
points; mesh 0.15 x 0.25 mm.

pad_stiffness: how stiffly each pad holds the panel's border (the retention review): the same plate carried on to the
pad's far edge (PAD_X[1]), the pad block solid from the panel's front to the skin or the bevel, the ribs as above,
1 N spread over the pad's contact on the panel (from the PS film's edge, X 1.777, to PAD_X[1]), no pad supports;
k = 1 / the load-weighted mean deflection."""
import math
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl
import params as P

NU = 0.35


def _mono(x, y):
    return np.array([1, x, y, x * x, x * y, y * y, x ** 3, x * x * y, x * y * y, y ** 3, x ** 3 * y, x * y ** 3])


def _dx(x, y):
    return np.array([0, 1, 0, 2 * x, y, 0, 3 * x * x, 2 * x * y, y * y, 0, 3 * x * x * y, y ** 3])


def _dy(x, y):
    return np.array([0, 0, 1, 0, x, 2 * y, 0, x * x, 2 * x * y, 3 * y * y, x ** 3, 3 * x * y * y])


def _curv(x, y):
    return np.array([[0, 0, 0, 2, 0, 0, 6 * x, 2 * y, 0, 0, 6 * x * y, 0],
                     [0, 0, 0, 0, 0, 2, 0, 0, 2 * x, 6 * y, 0, 6 * x * y],
                     [0, 0, 0, 0, 2, 0, 0, 4 * x, 4 * y, 0, 6 * x * x, 6 * y * y]])


_G, _GW = np.polynomial.legendre.leggauss(4)


def _element(a, b, t, E):
    nodes = [(0, 0), (a, 0), (a, b), (0, b)]
    Ci = np.linalg.inv(np.array([f(x, y) for x, y in nodes for f in (_mono, _dx, _dy)]))
    D = E * t ** 3 / (12 * (1 - NU ** 2)) * np.array([[1, NU, 0], [NU, 1, 0], [0, 0, (1 - NU) / 2]])
    K, N = np.zeros((12, 12)), np.zeros(12)
    for i, xi in enumerate(_G):
        for j, eta in enumerate(_G):
            x, y = a * (xi + 1) / 2, b * (eta + 1) / 2
            w = _GW[i] * _GW[j] * a * b / 4
            B = _curv(x, y)
            K += B.T @ D @ B * w
            N += _mono(x, y) * w
    return Ci.T @ K @ Ci, Ci.T @ N


def geometry():
    x_wall = P.STRIP_RIBS['x0']
    x_edge = P.CHANNEL_TOP - (P.Z_FRONT - P.WINDOW_CHAMFER)          # bevel at the ceiling: 0.8 in from the window
    x_edge = P.CHANNEL_X1 - 0.01 - x_edge                              # 2.0275
    x_full = x_edge - P.CHANNEL_SKIN                                   # 1.6275, bevel at the face
    return x_wall, x_edge, x_full


def _top(x):
    """The skin's top: the face, then the window's 45-degree bevel."""
    return min(P.Z_FRONT, (P.Z_FRONT - P.WINDOW_CHAMFER) + (P.CHANNEL_X1 - 0.01) - x)


def _on_rib(xc, yc, ribs):
    R = P.PAD_RIBS
    return ribs and xc < P.PAD_X[0] and any(abs(yc - py) <= R['len'] / 2 for py in R['y'])


def solve(load, E=3000.0, pads=P.PAD_Y, dxm=0.15, dym=0.25, ribs=True):
    """load = dict(F, x, y, r): F newtons spread evenly over the part of a disc (centre x, y, radius r) that lies on
    the skin. Returns (xs, ys, W, pad reactions): W[j, i] the deflection (mm, toward the panel) at (xs[i], ys[j])."""
    X0, X1, Xf = geometry()
    Y0, Y1 = P.CHANNEL_Y
    nx, ny = max(4, int(round((X1 - X0) / dxm))), int(round((Y1 - Y0) / dym))
    xs, ys = np.linspace(X0, X1, nx + 1), np.linspace(Y0, Y1, ny + 1)
    a, b = xs[1] - xs[0], ys[1] - ys[0]
    nid = lambda i, j: j * (nx + 1) + i
    ndof = 3 * (nx + 1) * (ny + 1)
    rows, cols, vals, F = [], [], [], np.zeros(ndof)
    cache = {}
    for j in range(ny):
        yc = (ys[j] + ys[j + 1]) / 2
        for i in range(nx):
            xc = (xs[i] + xs[i + 1]) / 2
            t = P.CHANNEL_SKIN if xc <= Xf else max(0.03, P.CHANNEL_SKIN - (xc - Xf))
            if _on_rib(xc, yc, ribs):
                t = _top(xc) - P.PAD_RIBS['z0']
            key = round(t, 4)
            if key not in cache:
                cache[key] = _element(a, b, t, E)
            Ke, Ne = cache[key]
            dofs = np.array([3 * n + k for n in (nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)) for k in range(3)])
            rr, cc = np.meshgrid(dofs, dofs, indexing='ij')
            rows.append(rr.ravel()); cols.append(cc.ravel()); vals.append(Ke.ravel())
            if (xc - load['x']) ** 2 + (yc - load['y']) ** 2 <= load['r'] ** 2:
                F[dofs] += Ne
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(ndof, ndof))
    F *= load['F'] / F[0::3].sum()
    fixed = {3 * nid(0, j) + k for j in range(ny + 1) for k in range(3)}
    fixed |= {3 * nid(i, j) + k for i in range(nx + 1) for j in (0, ny) for k in range(3)}
    padn = {py: [nid(i, j) for j in range(ny + 1) if abs(ys[j] - py) <= P.PAD_LEN / 2 + 1e-9
                 for i in range(nx + 1) if xs[i] >= P.PAD_X[0] - 1e-9] for py in pads}
    fixed |= {3 * n for ns in padn.values() for n in ns}
    free = np.array(sorted(set(range(ndof)) - fixed))
    u = np.zeros(ndof)
    u[free] = spl.spsolve(K[free][:, free].tocsc(), F[free])
    R = K @ u - F
    return xs, ys, u[0::3].reshape(ny + 1, nx + 1), {py: -float(sum(R[3 * n] for n in ns)) for py, ns in padn.items()}


def over_leds(xs, ys, W, leds):
    """Largest deflection of the skin over each LED's footprint (X STRIP_LED_X, its 4.0 length)."""
    n = (xs >= P.STRIP_LED_X[0]) & (xs <= P.STRIP_LED_X[1])
    return {ref: float(W[np.ix_((ys >= y - 2.0) & (ys <= y + 2.0), n)].max()) for ref, y in leds}


PS_X0 = 1.777462                          # the PS film's left edge (the panel's X0 + 0.65): where a pad meets the panel


def _grid(keys, h):
    ks = sorted(keys)
    out = [ks[0]]
    for a, b in zip(ks[:-1], ks[1:]):
        n = max(1, int(math.ceil((b - a) / h - 1e-9)))
        out += list(np.linspace(a, b, n + 1)[1:])
    return np.array(out)


def pad_stiffness(E=3000.0, ribs=True, dxm=0.1, dym=0.125):
    """{pad Y: k (N/mm)} for pads 1-4 (see the module's docstring). Each pad is loaded alone."""
    X0, X1 = P.STRIP_RIBS['x0'], P.PAD_X[1]
    Y0, Y1 = P.CHANNEL_Y
    R = P.PAD_RIBS
    xs = _grid({X0, X1, P.PAD_X[0], PS_X0, geometry()[2], geometry()[1]}, dxm)
    yk = {Y0, Y1}
    for py in P.PAD_Y:
        for h in (P.PAD_LEN / 2, R['len'] / 2):
            yk |= {v for v in (py - h, py + h) if Y0 < v < Y1}
    ys = _grid(yk, dym)
    nx, ny = len(xs) - 1, len(ys) - 1
    nid = lambda i, j: j * (nx + 1) + i
    ndof = 3 * (nx + 1) * (ny + 1)

    def thick(xc, yc):
        if xc >= P.PAD_X[0] and any(abs(yc - py) <= P.PAD_LEN / 2 for py in P.PAD_Y):
            return _top(xc) - P.LIP                                  # the pad block
        if _on_rib(xc, yc, ribs):
            return _top(xc) - R['z0']
        return max(0.03, min(P.CHANNEL_SKIN, _top(xc) - P.CHANNEL_TOP))

    rows, cols, vals, elems, cache = [], [], [], [], {}
    for j in range(ny):
        for i in range(nx):
            a, b = xs[i + 1] - xs[i], ys[j + 1] - ys[j]
            xc, yc = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            key = (round(a, 6), round(b, 6), round(thick(xc, yc), 4))
            if key not in cache:
                cache[key] = _element(a, b, key[2], E)
            dofs = np.array([3 * n + k for n in (nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)) for k in range(3)])
            rr, cc = np.meshgrid(dofs, dofs, indexing='ij')
            rows.append(rr.ravel()); cols.append(cc.ravel()); vals.append(cache[key][0].ravel())
            elems.append((xc, yc, key, dofs))
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(ndof, ndof))
    fixed = {3 * nid(0, j) + k for j in range(ny + 1) for k in range(3)}
    fixed |= {3 * nid(i, j) + k for i in range(nx + 1) for j in (0, ny) for k in range(3)}
    free = np.array(sorted(set(range(ndof)) - fixed))
    lu = spl.splu(K[free][:, free].tocsc())
    out = {}
    for py in P.PAD_Y[:4]:
        F = np.zeros(ndof)
        for xc, yc, key, dofs in elems:
            if xc >= PS_X0 and abs(yc - py) <= P.PAD_LEN / 2:
                F[dofs] += cache[key][1]
        F /= F[0::3].sum()
        u = np.zeros(ndof)
        u[free] = lu.solve(F[free])
        out[py] = float(1.0 / (F @ u))
    return out
