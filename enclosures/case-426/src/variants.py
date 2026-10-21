"""The 4.26 case's configurations: four axes, one slug each (2026-10-07). Standard library only and no side effects,
so params.py, build.py and pipeline.py (which must not import params: that creates out/ and loads the board) all
read the one source.

    slug  := base [ '-' sides ] [ '-nodev' ]
    base  := standard               the FT01C touch + frontlight panel, bottom keys
           | light-strip            the plain GDEY0426T82 + the Silkscreen light strip, bottom keys
           | chinless               the FT01C, no bottom keys (117.4 mm)
           | light-strip-chinless   the plain panel + the light strip, no bottom keys (117.4 mm)
    sides := (none)      all four page keys: L-up SW7, L-down SW5, R-up SW4, R-down SW1
           | leftkeys    the LEFT pair only: SW7 (upper), SW5 (lower)
           | rightkeys   the RIGHT pair only: SW4 (upper), SW1 (lower)
           | upperkeys   the upper key on each side: SW7 (left), SW4 (right)
    nodev  J6 (the dev header) not fitted

LEFT and RIGHT are as the case is held, screen toward you, top up: CAD +X is the user's RIGHT (hw.RIGHT_SWITCHES).
SW10 (power) is on every case: the RIGHT edge, at the top; the USB-C port is lower on the same edge, below the
right pair. A key a layout leaves out is the plain wall, in the tub and in the lid; its switch may stay fitted.
Each configuration has exactly one slug: the tokens in this order, at most one side set, no aliases.
"""
from collections import namedtuple

# base: (panel, bottom keys)
BASES = {'standard': ('standard', True), 'light-strip': ('light-strip', True),
         'chinless': ('standard', False), 'light-strip-chinless': ('light-strip', False)}
# the side keys each layout has (params.TAB_ROOTS keeps these): SW10, power, in every one
SIDE_SETS = {'all': ('SW1', 'SW4', 'SW10', 'SW5', 'SW7'), 'leftkeys': ('SW10', 'SW5', 'SW7'),
             'rightkeys': ('SW1', 'SW4', 'SW10'), 'upperkeys': ('SW4', 'SW10', 'SW7')}
OPTIONS = ('leftkeys', 'rightkeys', 'upperkeys', 'nodev')          # their order in a slug
AXES = ('panel', 'chin', 'sides', 'dev')
DEFAULT = {'panel': 'standard', 'chin': True, 'sides': 'all', 'dev': True}
Config = namedtuple('Config', 'slug base panel bottom_keys sides dev opts')


def parse(slug):
    """slug -> Config. Raises ValueError on anything that is not exactly one configuration's slug."""
    base = next((b for b in sorted(BASES, key=len, reverse=True) if slug == b or slug.startswith(b + '-')), None)
    opts = tuple(slug[len(base) + 1:].split('-')) if base and slug != base else ()
    sides = [o for o in opts if o in SIDE_SETS]
    if (base is None or any(o not in OPTIONS for o in opts) or list(opts) != sorted(set(opts), key=OPTIONS.index)
            or len(sides) > 1):
        raise ValueError(f'SILKSCREEN_VARIANT={slug!r}: use <{"|".join(BASES)}>[-leftkeys|-rightkeys|-upperkeys][-nodev]')
    panel, keys = BASES[base]
    return Config(slug, base, panel, keys, sides[0] if sides else 'all', 'nodev' not in opts, opts)


def make(panel, bottom_keys, sides='all', dev=True):
    """The slug of a configuration given by its axes."""
    base = next(b for b, v in BASES.items() if v == (panel, bottom_keys))
    assert sides in SIDE_SETS, sides
    return '-'.join(x for x in (base, '' if sides == 'all' else sides, '' if dev else 'nodev') if x)


def axes(slug):
    """{'panel': ..., 'chin': bottom keys, 'sides': ..., 'dev': J6 fitted}"""
    c = parse(slug)
    return {'panel': c.panel, 'chin': c.bottom_keys, 'sides': c.sides, 'dev': c.dev}


def twin(slug, axis):
    """The slug with that axis at its default (panel -> standard, chin -> bottom keys, sides -> all four,
    dev -> J6): the configuration this one is proven against on that axis."""
    a = axes(slug)
    a[axis] = DEFAULT[axis]
    return make(a['panel'], a['chin'], a['sides'], a['dev'])


def twins(slug):
    """[(axis, twin)] for every axis on which slug is not the default, in AXES order."""
    a = axes(slug)
    return [(x, twin(slug, x)) for x in AXES if a[x] != DEFAULT[x]]


ALL = tuple(make(p, k, s, d) for (p, k) in BASES.values() for s in SIDE_SETS for d in (True, False))   # the 32
SIX = ('standard', 'light-strip', 'chinless', 'standard-nodev', 'light-strip-nodev', 'chinless-nodev')  # before 2026-10-07
# print/4.26/ and the plate file are made from these (light-strip-chinless since 2026-10-07: its tub, plate 5)
PRINT_BUILDS = ('standard', 'light-strip', 'chinless', 'light-strip-chinless')


def rank(slug):
    """Build order, longest first: keyed before chinless; all four side keys before the side sets (they wait for
    their all-keys twin); J6 before nodev; light strip before standard. The six keep their order of 2026-10-06
    (light-strip, standard, light-strip-nodev, standard-nodev, chinless, chinless-nodev)."""
    c = parse(slug)
    return (not c.bottom_keys, list(SIDE_SETS).index(c.sides), not c.dev, c.panel != 'light-strip')


ORDER = tuple(sorted(ALL, key=rank))
