"""Which of the two builds of the 3.68in case this run makes: SILKSCREEN_VARIANT=standard or light-strip.

Both come from one code base (Ian's rule, 2026-09-26): every printed part but the tub is the same part in both, so an
owner who adds the light strip prints one extra part. params.py reads this and gates what differs on LIGHT_STRIP;
build.py builds both (one subprocess each) and asserts that the shared parts come out identical.
light-strip is the default, so a script run on its own builds what this copy built before the split.
"""
import os

VARIANTS = ('standard', 'light-strip')
NAME = os.environ.get('SILKSCREEN_VARIANT', 'light-strip')
if NAME not in VARIANTS:
    raise SystemExit(f'SILKSCREEN_VARIANT={NAME!r}: expected one of {VARIANTS}')
LIGHT_STRIP = NAME == 'light-strip'
