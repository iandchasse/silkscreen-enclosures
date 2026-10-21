"""Unit test of the slug grammar (variants.py) and of the axes params.py reads from it (2026-10-07).

    python -B src/test_variants.py          (from enclosures/case-426; about 10 s: it imports params once per slug)

No CAD is built. The params part imports params under every slug (in one child process, reloading it) and leaves
out/ as it found it (an out/<slug>/ that params' import creates is removed again when it is empty).
"""
import json, os, subprocess, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import variants as V

ROOTS = {'SW1': 49.5, 'SW4': 87.3, 'SW10': 106.0, 'SW5': 46.0, 'SW7': 91.0}
# params under today's six slugs as 20c3021 (the last commit before the variants) had them: (VARIANT, OPTS,
# LIGHT_STRIP, BOTTOM_KEYS, DEV_HEADER, TAB_ROOTS in order, hw.DNP)
R0 = {'standard': ('standard', (), False, True, True, ROOTS, ()),
      'light-strip': ('light-strip', (), True, True, True, ROOTS, ()),
      'chinless': ('chinless', (), False, False, True, ROOTS, ('SW2', 'SW3', 'SW8', 'SW9')),
      'standard-nodev': ('standard', ('nodev',), False, True, False, ROOTS, ('J6',)),
      'light-strip-nodev': ('light-strip', ('nodev',), True, True, False, ROOTS, ('J6',)),
      'chinless-nodev': ('chinless', ('nodev',), False, False, False, ROOTS, ('J6', 'SW2', 'SW3', 'SW8', 'SW9'))}
REJECT = ('standard-chinless', 'chinless-light-strip', 'standard-nodev-upperkeys', 'light-strip-chinless-nodev-upperkeys',
          'standard-leftkeys-rightkeys', 'upperkeys', 'nodev', 'light-strip-chinless-chinless', 'standard-allkeys',
          'standard-all', 'Standard', '', 'standard-', 'standard--nodev', 'standard-nodev-nodev', 'chinless-left',
          'light-strip-leftkeys-leftkeys')


def test_grammar():
    assert len(V.ALL) == 32 and len(set(V.ALL)) == 32, V.ALL
    assert set(V.SIX) <= set(V.ALL) and set(V.PRINT_BUILDS) <= set(V.ALL)
    n = 0
    for (panel, keys) in V.BASES.values():
        for sides in V.SIDE_SETS:
            for dev in (True, False):
                s = V.make(panel, keys, sides, dev)
                c = V.parse(s)
                assert (c.slug, c.panel, c.bottom_keys, c.sides, c.dev) == (s, panel, keys, sides, dev), (s, c)
                assert V.make(c.panel, c.bottom_keys, c.sides, c.dev) == s
                n += 1
    assert n == 32
    for s in REJECT:
        try:
            V.parse(s)
        except ValueError:
            continue
        raise AssertionError(f'{s!r} was accepted')
    # the six keep their names and meaning
    for s, r in R0.items():
        c = V.parse(s)
        assert (c.base, c.opts, c.panel == 'light-strip', c.bottom_keys, c.dev, c.sides) == (*r[:5], 'all'), (s, c)


def test_side_sets():
    import hw
    left, right = set(hw.LEFT_SWITCHES), set(hw.RIGHT_SWITCHES)
    assert set(V.SIDE_SETS['all']) == left | right
    for name, keys in V.SIDE_SETS.items():
        assert 'SW10' in keys, name                          # power on every case
        assert set(keys) <= left | right, name
    assert set(V.SIDE_SETS['leftkeys']) - {'SW10'} == left    # as held: CAD -X is the user's left
    assert set(V.SIDE_SETS['rightkeys']) == right
    assert set(V.SIDE_SETS['upperkeys']) == {'SW7', 'SW4', 'SW10'}   # SW7 left-upper, SW4 right-upper
    ys = {r: hw.switch_plunger(r)['face'][1] for r in left | right}
    assert ys['SW7'] > ys['SW5'] and ys['SW4'] > ys['SW1']   # 'upper' is the higher one on each side


def test_twins():
    for s in V.ALL:
        a = V.axes(s)
        ts = V.twins(s)
        assert [x for x, _ in ts] == [x for x in V.AXES if a[x] != V.DEFAULT[x]], s
        for axis, t in ts:
            b = V.axes(t)
            assert b[axis] == V.DEFAULT[axis] and all(b[x] == a[x] for x in V.AXES if x != axis), (s, axis, t)
    assert V.twin('light-strip-chinless-upperkeys-nodev', 'panel') == 'chinless-upperkeys-nodev'
    assert V.twin('light-strip-chinless-upperkeys-nodev', 'chin') == 'light-strip-upperkeys-nodev'
    assert V.twin('light-strip-chinless-upperkeys-nodev', 'sides') == 'light-strip-chinless-nodev'
    assert V.twin('light-strip-chinless-upperkeys-nodev', 'dev') == 'light-strip-chinless-upperkeys'
    assert V.twins('standard') == []


def test_order():
    assert sorted(V.ORDER) == sorted(V.ALL)
    six = [s for s in V.ORDER if s in V.SIX]                 # their order of 2026-10-06 (pipeline.PRIORITY then)
    assert six == ['light-strip', 'standard', 'light-strip-nodev', 'standard-nodev', 'chinless', 'chinless-nodev'], six
    for s in V.ALL:                                          # a twin it reads from is never after it
        for axis, t in V.twins(s):
            if axis in ('chin', 'sides'):
                assert V.ORDER.index(t) < V.ORDER.index(s), (s, t)


CHILD = r'''
import importlib, json, os, sys
sys.path.insert(0, os.getcwd())
out = {}
P = None
for s in sys.argv[1:]:
    os.environ['SILKSCREEN_VARIANT'] = s
    if P is None:
        import params as P
    else:
        P = importlib.reload(P)
    import hw
    out[s] = [P.VARIANT, list(P.OPTS), P.LIGHT_STRIP, P.BOTTOM_KEYS, P.DEV_HEADER, list(P.TAB_ROOTS.items()),
              sorted(hw.DNP), P.SIDES, list(P.SIDE_REFS), list(P.TAB_ROOTS_ALL.items())]
print(json.dumps(out))
'''


def test_params():
    out_dir = SRC.parent / 'out'
    before = {s for s in V.ALL if (out_dir / s).exists()}
    env = {k: v for k, v in os.environ.items() if k != 'SILKSCREEN_VARIANT'}
    try:
        r = subprocess.run([sys.executable, '-B', '-c', CHILD, *V.ALL], cwd=SRC, env=env, capture_output=True, text=True)
    finally:
        for s in V.ALL:
            d = out_dir / s
            if s not in before and d.exists() and not any(d.iterdir()):
                d.rmdir()
    assert r.returncode == 0, r.stderr[-3000:]
    got = json.loads(r.stdout)
    for s, (var, opts, ls, bk, dev, roots, dnp) in R0.items():
        g = got[s]
        assert (g[0], tuple(g[1]), g[2], g[3], g[4]) == (var, opts, ls, bk, dev), (s, g)
        assert g[5] == [list(x) for x in roots.items()], (s, g[5])        # the same keys in the same order
        assert tuple(g[6]) == dnp, (s, g[6])
    for s in V.ALL:
        c = V.parse(s)
        g = got[s]
        assert (g[2], g[3], g[4], g[7]) == (c.panel == 'light-strip', c.bottom_keys, c.dev, c.sides), (s, g)
        assert g[9] == [list(x) for x in ROOTS.items()], s
        assert [r for r, _ in g[5]] == [r for r in ROOTS if r in V.SIDE_SETS[c.sides]], (s, g[5])
        assert all(ROOTS[r] == y for r, y in g[5]), s
        want_dnp = sorted((['SW2', 'SW3', 'SW8', 'SW9'] if not c.bottom_keys else []) + ([] if c.dev else ['J6']))
        assert g[6] == want_dnp, (s, g[6])                    # the side switches stay in the model in every layout


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            print(f'PASS {name}', flush=True)
    print('test_variants: all pass')
