"""Snap force and strain estimates for the prong (BEAM ESTIMATES, nothing here is measured on a print).

The prong is a cantilever along u (root at u_root, loaded at the ridge) that bends in the layer plane about a vertical edge,
so its bending stress runs along the printed lines. Its stiffness is integrated over the tapered thickness (0.8 at the tip
to tw at the root); the width is the ridge's height (the loaded band: soft bound) to the prong's whole height (stiff bound).

The case's plan arc and the ridge profile give the deflection the prong needs at every cover position s (the cover moves
by s along x: case x = u + s, home at s = -cx). Contact forces: the normal force is k * deflection; the force along the
slide is N (g + mu) / (1 - mu g) up a slope g = d(deflection)/d(slide), signed (negative = the spring pulls the cover on).

    python -B snap.py            prints the table for the cover groups
"""
import math

import numpy as np

import model as M

E_PLA = (2500.0, 3000.0, 3500.0)       # MPa, printed PLA along the lines (the middle one is the nominal)
MU = (0.2, 0.3, 0.4)                    # PLA on PLA


def case_profile(s, x):
    """The case's end face at plan x, as y - Y1 (<= 0): the flat between the R arcs, the arcs outside; -inf off the case."""
    R = s['CORNER_R']
    xa, xb = s['X0'] + R, s['X1'] - R
    x = np.asarray(x, dtype=float)
    y = np.full(x.shape, -np.inf)
    inside = (x >= s['X0']) & (x <= s['X1'])
    d = np.where(x < xa, xa - x, np.where(x > xb, x - xb, 0.0))
    y[inside] = (-R + np.sqrt(np.maximum(R * R - d[inside] ** 2, 0.0)))
    return y


def ridge_profile(s, n=400):
    """The ridge's inner surface in (u, y - Y1): tip level -d_eng, wall plane +cy; u from u_a to the removal ramp's foot."""
    cy, d = s['cy'], s['d_eng']
    ua, ri, f, rr = s['u_a'], s['r_i'], s['f_top'], s['r_r']
    u = np.linspace(ua, ua + ri + f + rr, n)
    y = np.interp(u, [ua, ua + ri, ua + ri + f, ua + ri + f + rr], [cy, -d, -d, cy])
    return u, y


def deflection(s, shifts):
    """The prong's required outward deflection at each cover shift (cover u -> case x = u + shift)."""
    u, yb = ridge_profile(s)
    out = []
    for sh in shifts:
        yc = case_profile(s, u + sh)
        out.append(max(0.0, float(np.max(yc - yb))))
    return np.array(out)


def stiffness(s, E, b):
    """Tip stiffness (N/mm) at the load point, strain per unit force at the worst section (1/N), for a prong of width b.
    The load acts at the middle of the ridge's flat top, L from the root."""
    L = s['u_root'] - (s['u_t'] - s['f_top'] / 2)
    xs = np.linspace(0.0, L, 2001)                       # from the root
    tw, tp, tap = s['tw'], s['t_pr'], s['taper']
    t = np.where(xs < tap, tw + (tp - tw) * xs / tap, tp)
    I = b * t ** 3 / 12.0
    # deflection at the load point from a unit force there: integral of (L - x)^2 / (E I) dx
    comp = np.trapezoid((L - xs) ** 2 / (E * I), xs)
    k = 1.0 / comp
    eps = 6.0 * (L - xs) / (E * b * t ** 2)               # strain per N at each section: M (t/2) / (E I), M = F (L - x)
    return k, float(eps.max()), L


def forces(s, E=3000.0, b=None, mu=0.3):
    """-> dict with the stiffness, the force-vs-shift table and the peaks."""
    if b is None:
        b = 2 * s['ridge_half']
    k, eps1, L = stiffness(s, E, b)
    shifts = np.arange(-s['cx'], 70.0, 0.02)
    dl = deflection(s, shifts)
    N = k * dl
    g = np.gradient(dl, shifts)
    pull = N * (g + mu) / (1 - mu * g)                   # cover moving +x (off)
    push = N * (-g + mu) / (1 + mu * g)                  # cover moving -x (on): sign of g flips
    # push: moving -x, the slope seen is -g; uphill when -g > 0 ... use the same wedge law with g -> -g
    gi = -g
    push = N * (gi + mu) / (1 - mu * gi)
    home = int(np.argmin(np.abs(shifts + s['cx'])))
    mid = int(np.argmin(np.abs(shifts - 30.0)))
    iwin = shifts < 12.0                                  # the removal path: the corner region
    iins = shifts > 55.0                                  # the insertion path: the other corner
    d_max = float(dl.max())
    return dict(k=k, L=L, b=b, E=E, mu=mu, shifts=shifts, defl=dl, N=N, pull=pull, push=push,
                N_slide=float(N[mid]), friction_slide=float(mu * N[mid]),
                pull_peak=float(pull[iwin].max()), pull_peak_at=float(shifts[iwin][np.argmax(pull[iwin])]),
                push_peak=float(push[iins | (shifts > 40)].max()),
                push_peak_at=float(shifts[iins | (shifts > 40)][np.argmax(push[iins | (shifts > 40)])]),
                home_preload_N=float(N[home]), d_max=d_max, strain=float(eps1 * N.max()))


def table(s, label=''):
    rows = []
    for E in E_PLA:
        for b in (2 * s['ridge_half'], s['z_o'] - s['prong_z_lo']):
            for mu in MU:
                r = forces(s, E, b, mu)
                rows.append(r)
    return rows


if __name__ == '__main__':
    for grp in ('keyed', 'chinless', 'x3'):
        for d in (0.5, 0.6, 0.7, 0.8, 1.0):
            s = M.spec(grp, d_eng=d)
            r0 = forces(s)
            lo = min(r['pull_peak'] for r in table(s))
            hi = max(r['pull_peak'] for r in table(s))
            print(f"{grp:8s} d_eng {d:.1f}: k {r0['k']:.2f} N/mm (L {r0['L']:.1f}), N on the flat {r0['N_slide']:.2f} N, slide "
                  f"{r0['friction_slide']:.2f} N/prong, pull peak {r0['pull_peak']:.2f} N/prong at s={r0['pull_peak_at']:.1f} "
                  f"(range {lo:.2f}-{hi:.2f}), push peak {r0['push_peak']:.2f}, preload {r0['home_preload_N']:.2f}, "
                  f"strain {100 * r0['strain']:.2f} %")
        if grp == 'keyed':
            break


def wedge(shifts, dl, k, mu, s):
    """Forces from a measured deflection path dl(shifts) (check.py reads it off the real end faces): one prong, stiffness k
    (N/mm), friction mu. pull = the force to draw the cover off (shift increasing), push = to put it on, drag = the
    friction while it slides on the flat, preload = the prong's force at home."""
    N = k * dl
    g = np.gradient(dl, shifts)
    pull = N * (g + mu) / (1 - mu * g)
    gi = -g
    push = N * (gi + mu) / (1 - mu * gi)
    fa = s['X0'] + s['CORNER_R'] + 0.5 - s['u_a']
    fb = s['X1'] - s['CORNER_R'] - 0.5 - (s['u_a'] + s['r_i'] + s['f_top'] + s['r_r'])
    iw = shifts <= fa + 2.0
    ii = shifts >= fb - 2.0
    mid = (shifts >= fa) & (shifts <= fb)
    home = int(np.argmin(np.abs(shifts + s['cx'])))
    return dict(pull_peak=float(pull[iw].max()), push_peak=float(push[ii].max()), drag=float(mu * N[mid].mean()),
                preload=float(N[home]), pull_at=float(shifts[iw][np.argmax(pull[iw])]))
