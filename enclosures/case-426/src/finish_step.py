"""pipeline.py's finish-only step (2026-10-08): build.py --finish <builds> --only, with each share claim (build.compare_parts:
a build's parts against a twin's) memoised by the bytes it compares.

    python -B src/finish_step.py <builds>          (= python -B src/build.py --finish <builds> --only, faster)

A claim's result is a function of the code (every module build.py imports, but the runner's: pipeline, _step and
jobs, which build.py imports only to run its builds through pipeline.py), the environment (cache.env_fingerprint: the
interpreter and packages, as in every step's key; compare_parts runs OCCT) and the STL and STEP bytes of the parts it
names in both folders, so it is stored under exactly those (cache.memo 'share-claims'; a rebuild's new STEP export
time only misses). Exact by construction here: after the claims, finish --only writes nothing but the
claims' JSON (out/<build>/shared.json, out/shares-all.json). Not in finish-default, whose print/4.26/ STEP exports
follow the claims and number themselves per process (OCCT's 'translator 7.9 N'). No step imports this file, so no
step's key holds it; the steps that run it (finish-only) are not cached.
"""
import hashlib, sys
import cache
import build as B

_orig = B.compare_parts
_CODE = None
RUNNER = ('pipeline', '_step', 'jobs')      # = pipeline.NOT_CODE: in no claim's computation


def _code():
    global _CODE
    if _CODE is None:
        _CODE = {'src': {m: cache.sha((cache.SRC / f'{m}.py').read_bytes()) for m in cache.closure('build')
                         if m not in RUNNER},
                 'env': cache.env_fingerprint()}
    return _CODE


def _sha(p):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def compare_parts(dir_a, dir_b, names):
    parts = {'code': _code(), 'names': list(names),
             'files': {n: [_sha(d / f'{n}.{x}') for d in (dir_a, dir_b) for x in ('stl', 'step')] for n in names}}
    return cache.memo('share-claims', parts, lambda: _orig(dir_a, dir_b, names))


if __name__ == '__main__':
    B.compare_parts = compare_parts
    B.finish([b for b in sys.argv[1].split(',') if b], True)
