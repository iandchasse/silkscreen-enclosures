"""Run in a subprocess by case_info.py: import a case's own logo.py and params.py (read-only, with SILKSCREEN_VARIANT set) and print
the back logos as the case places them, in the case's CAD frame: {"icon": {...}, "wordmark": {...}} with WKT polygons (mm), the engraving
depth and the back face's z. The cover engraves the same shapes."""
import json
import os
import sys

case, slug, root = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ['SILKSCREEN_VARIANT'] = slug
sys.path.insert(0, root + '/' + case + '/src')
os.chdir(root + '/' + case)
import logo                       # noqa: E402
import params as P                # noqa: E402

out = {'z_back': P.Z_BACK, 'layer': P.LAYER}
for name, cfg in (('icon', P.LOGO_BACK), ('wordmark', P.LOGO_BACK_WORDMARK)):
    g = logo.placed(cfg)
    out[name] = {'wkt': g.wkt, 'depth': cfg['depth'], 'bounds': list(g.bounds), 'mirror': bool(cfg.get('mirror')), 'y': cfg['y'], 'x': cfg['x']}
print(json.dumps(out))
