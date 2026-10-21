"""One pipeline step (src/pipeline.py): runs a script exactly as `python -B src/<script> <args>` would, and records
every file it reads, lists and writes in the repo, so the runner can refuse to cache a step that read something
its key does not cover (an undeclared input) or wrote outside its outputs. It records those in the cache and memo
folders too when SILKSCREEN_CACHE or SILKSCREEN_MEMO puts them outside the repo, so the runner still learns which
memo files a step read (pipeline.memos_of: a kept entry keeps the memos it names).

    python -B src/_step.py <audit.json> <script.py> [args...]

What is seen: Python's own file access (sys.addaudithook: open, os.listdir/scandir, glob, remove, rename, copy),
the file arguments of subprocesses (OrcaSlicer's), and the C++ readers wrapped below (cadquery's importStep and
Shape.importBrep / importBin). A new C++ reader of files (a cadquery importer, an OCP reader called directly) must
be added to _CPP_READERS, or its reads go unseen. Nothing else changes: the script runs as __main__ with its own
sys.argv and sys.path[0] (src/), in this process.
"""
import json, os, sys

REPO = os.path.normcase(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
# what is recorded: the repo, and the cache and memo folders where cache.py puts them (SILKSCREEN_CACHE,
# SILKSCREEN_MEMO; unset, both are in the repo: out/.cache/, out/.cache/memo/)
_cache = os.path.realpath(os.environ['SILKSCREEN_CACHE']) if os.environ.get('SILKSCREEN_CACHE') else None
_memo = (os.path.realpath(os.environ['SILKSCREEN_MEMO']) if os.environ.get('SILKSCREEN_MEMO')
         else os.path.join(_cache, 'memo') if _cache else None)
_ROOTS = tuple(os.path.normcase(p) + os.sep for p in (REPO, _cache, _memo) if p)
_reads, _writes, _lists = set(), set(), set()
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def _norm(p):
    if isinstance(p, int):
        return None
    try:
        p = os.fsdecode(os.fspath(p))
    except TypeError:
        return None
    p = os.path.normcase(os.path.abspath(p))
    return p if p.startswith(_ROOTS) else None


def _hook(event, args):
    if event == 'open':
        p = _norm(args[0])
        if p:
            mode, flags = args[1], args[2]
            w = any(c in mode for c in 'wax+') if isinstance(mode, str) else bool((flags or 0) & _WRITE_FLAGS)
            (_writes if w else _reads).add(p)
    elif event in ('os.listdir', 'os.scandir', 'glob.glob'):
        p = _norm(args[0] if args[0] is not None else '.')
        if p:
            _lists.add(p)
    elif event in ('os.remove', 'os.rmdir'):
        p = _norm(args[0])
        if p:
            _writes.add(p)
    elif event in ('os.rename', 'shutil.copyfile', 'shutil.move'):
        a, b = _norm(args[0]), _norm(args[1])
        if a:
            (_writes if event != 'shutil.copyfile' else _reads).add(a)
        if b:
            _writes.add(b)
    elif event == 'subprocess.Popen':
        for a in (args[1] or []):
            for part in str(a).split(';'):
                p = _norm(part) if os.path.isabs(part) else None
                if p:
                    _reads.add(p)


def _wrap(fn):
    def reader(*a, **k):
        for x in list(a[:1]) + [k.get('fileName'), k.get('f')]:
            p = _norm(x) if isinstance(x, (str, os.PathLike)) else None
            if p:
                _reads.add(p)
        return fn(*a, **k)
    reader.__wrapped__ = fn
    return reader


def _patch_cadquery(cq):
    """cadquery's C++ file readers, so their reads are recorded too."""
    cq.importers.importStep = _wrap(cq.importers.importStep)
    for name in ('importBrep', 'importBin'):            # classmethods: keep the class they are called on
        f = cq.Shape.__dict__.get(name)
        if isinstance(f, classmethod):
            def reader(cls, path, *a, _f=f.__func__, **k):
                p = _norm(path) if isinstance(path, (str, os.PathLike)) else None
                if p:
                    _reads.add(p)
                return _f(cls, path, *a, **k)
            setattr(cq.Shape, name, classmethod(reader))


class _CadqueryHook:
    """Patches cadquery when the script first imports it (importing it here would change the order the native
    libraries load in)."""

    def find_spec(self, name, path, target=None):
        if name != 'cadquery':
            return None
        import importlib.util
        sys.meta_path.remove(self)
        spec = importlib.util.find_spec(name)
        run = spec.loader.exec_module

        def exec_module(module):
            run(module)
            _patch_cadquery(module)
        spec.loader.exec_module = exec_module
        return spec


def _save(path, code):
    with open(path, 'w') as f:
        json.dump({'exit': code, 'reads': sorted(_reads), 'writes': sorted(_writes), 'lists': sorted(_lists)}, f)


if __name__ == '__main__':
    audit, script, args = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3:]
    sys.argv = [script, *args]
    sys.path[0] = os.path.dirname(script)
    sys.meta_path.insert(0, _CadqueryHook())
    sys.addaudithook(_hook)
    import runpy
    code = 0
    try:
        runpy.run_path(script, run_name='__main__')
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if not isinstance(e.code, int) and e.code is not None:
            print(e.code, file=sys.stderr)
    except BaseException:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    _save(audit, code)
    sys.exit(code)
