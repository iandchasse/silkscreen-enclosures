"""Plot the drawing's front and back views in millimetres (origin: EPD bottom-left
corner as drawn in each view, u right, v up) so the ribbon outlines can be read."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
S = json.load(open('extract/segments_pt.json'))
s = 1.5042
views = {'front': (140.56, 237.16), 'back': None}
# back view EPD outline: find the rectangle whose bottom edge line sits at page x 237.52 near page y 552..646
bl = [x for x in S if abs(x[0] - x[2]) < 0.05 and 540 < min(x[1], x[3]) and max(x[1], x[3]) < 660 and abs(x[1] - x[3]) > 90]
u0b = min(min(x[1], x[3]) for x in bl)
views['back'] = (u0b, 237.16)
out = {}
fig, axes = plt.subplots(1, 2, figsize=(22, 13))
for ax, (name, (u0, v0)) in zip(axes, views.items()):
    segs = []
    for x0, y0, x1, y1, w in S:
        u_a, u_b = (y0 - u0) / s, (y1 - u0) / s
        v_a, v_b = (x0 - v0) / s, (x1 - v0) / s
        if -6 < min(u_a, u_b) and max(u_a, u_b) < 68 and -30 < min(v_a, v_b) and max(v_a, v_b) < 12:
            segs.append((round(u_a, 3), round(v_a, 3), round(u_b, 3), round(v_b, 3), w))
            ax.plot([u_a, u_b], [v_a, v_b], lw=0.4 + 1.2 * (w or 0), color='k')
    out[name] = segs
    ax.set_aspect('equal'); ax.set_xticks(range(-6, 69, 2)); ax.set_yticks(range(-30, 13, 1)); ax.grid(alpha=0.35, lw=0.4)
    ax.set_title(name + ' view (mm from EPD bottom-left)'); ax.tick_params(labelsize=6)
fig.tight_layout(); fig.savefig('extract/views_mm.png', dpi=110)
json.dump(out, open('extract/views_mm.json', 'w'))
print({k: len(v) for k, v in out.items()}, 'back u0', u0b)
