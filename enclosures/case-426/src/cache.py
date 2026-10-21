"""The build cache (2026-10-06): content-addressed, so a result is only ever served for exactly the inputs that
made it. Used by src/pipeline.py (the step cache: one script process for one build) and, inside the scripts, by
slice_check (the OrcaSlicer call and its preset index): the memos.

Where:  out/.cache/ (out/ is not in git), or SILKSCREEN_CACHE=<dir>; the memos alone can be shared between
        checkouts with SILKSCREEN_MEMO=<dir> (they hold no paths).
          blobs/ab/<sha256>            file bodies, content-addressed (a file the same in two builds is stored once)
          steps/<step>/<key>.json      one pipeline step's run: its key's parts, the files it wrote and deleted
          steps/<step>/last.json       the files that step owned after its last run or restore
          memo/<name>/ab/<key>.pkl     a memo's value (pickled: the types come back exactly); its file date is
                                       when it was last made or served (prune drops the ones unused MEMO_DAYS)
          stat.json                    (size, mtime) -> sha256 of the files the runner hashed, so warm runs read
                                       nothing twice (pipeline.py --rehash ignores it)
          run/                         locks, the build children's phase-1 markers, the step specs and audits
          logs/                        each step's console output
Mode:   SILKSCREEN_CACHE_MODE = on (the default) | refresh (compute everything and store it: what pipeline.py
        --no-cache does) | off (no cache at all: the scripts behave as before the cache, and pipeline.py runs every
        step and stores nothing). Under refresh a memo is computed once per run, not once per process: an entry
        made since SILKSCREEN_REFRESH_SINCE (the run's start; pipeline.py --no-cache sets it) is served, so every
        build of the run gets the same OrcaSlicer G-code of a shared part, as in a cached run, and --verify can
        replay it. Unset, refresh serves no memo.
Keys:   sha256 of their parts as JSON with sorted keys (digest); a part JSON cannot hold raises (a loud error,
        never a wrong key).

python -B src/cache.py stats | prune [--keep N] [--memo-days D] | clear
"""
import ast, hashlib, json, os, pickle, platform, re, shutil, subprocess, sys, threading, time, types, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # enclosures/case-426
SRC = ROOT / 'src'
REPO = ROOT.parents[1]
FORMAT = 'silkscreen-cache-1'                       # change it and every key changes
CACHE = Path(os.environ['SILKSCREEN_CACHE']).resolve() if os.environ.get('SILKSCREEN_CACHE') else ROOT / 'out' / '.cache'
MEMO = Path(os.environ['SILKSCREEN_MEMO']).resolve() if os.environ.get('SILKSCREEN_MEMO') else CACHE / 'memo'
MODE = os.environ.get('SILKSCREEN_CACHE_MODE', 'on')
assert MODE in ('on', 'refresh', 'off'), f'SILKSCREEN_CACHE_MODE {MODE!r}: on, refresh or off'
REFRESH_SINCE = float(os.environ.get('SILKSCREEN_REFRESH_SINCE') or 'inf')   # refresh: memos made since are this run's
MEMO_DAYS = 14                                      # prune: a memo entry not made or served for this long goes
STEP_NAME = re.compile(rb"FILE_NAME\(.*?\);", re.S)
# what the board tools regenerate in hardware/ and no step reads (gitignored): left out of the hardware key
HW_SKIP = {'board.stl', 'mechanical.json', 'step-export.log', 'silkscreen_pcb-portable.kicad_pcb'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def masked(path, b):
    """The bytes a file is compared by: a STEP without its FILE_NAME statement (the export time), else the file."""
    if Path(path).suffix.lower() in ('.step', '.stp'):
        return STEP_NAME.sub(b'FILE_NAME(<masked>);', b, count=1)
    return b


def digest(parts):
    return sha(json.dumps(parts, sort_keys=True, separators=(',', ':')).encode())


# ---------------------------------------------------------------- source closures
def imports_of(mod):
    """The src/ modules a src/ module imports, anywhere in it (inside functions too)."""
    t = ast.parse((SRC / f'{mod}.py').read_text(encoding='utf-8'))
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            out.add(n.module.split('.')[0])
    return {m for m in out if (SRC / f'{m}.py').exists()}


def closure(mod):
    """mod and every src/ module it imports, recursively: sorted names."""
    seen, todo = set(), [mod]
    while todo:
        m = todo.pop()
        if m not in seen:
            seen.add(m)
            todo += imports_of(m)
    return sorted(seen)


def env_fingerprint():
    """What, beyond the code, can change a number: the interpreter, every installed distribution, the CPU and the
    thread-count settings of the numeric libraries."""
    import importlib.metadata as md
    dists = sorted(f"{d.metadata['Name']}=={d.version}" for d in md.distributions())
    threads = {k: os.environ[k] for k in sorted(os.environ) if k.endswith('_NUM_THREADS') or k in ('KMP_AFFINITY',)}
    return {'python': sys.version, 'exe': sys.executable, 'dists': sha('\n'.join(dists).encode()),
            'cpu': platform.processor(), 'machine': platform.machine(), 'threads': threads,
            'test': os.environ.get('SILKSCREEN_CACHE_TEST_TOOLCHAIN', '')}


# ---------------------------------------------------------------- files
def atomic_write(path, data):
    """path gets data whole or not at all: written beside it, then renamed over it. On Windows a reader that holds
    the file open (a `tail -F`, an editor) can refuse the rename for a moment: retried for 2 s, then written in place
    (as the scripts themselves write)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp')
    tmp.write_bytes(data)
    for i in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.1)
    try:
        path.write_bytes(data)
    finally:
        tmp.unlink(missing_ok=True)


def blob_path(h):
    return CACHE / 'blobs' / h[:2] / h


def blob_put(path, h=None):
    b = Path(path).read_bytes()
    h = h or sha(b)
    if not blob_path(h).exists():
        try:
            atomic_write(blob_path(h), b)
        except OSError:                                 # another thread or process stored the same blob meanwhile
            try:
                if sha(blob_path(h).read_bytes()) == h:
                    return h
            except OSError:
                pass
            raise
    return h


def blob_ok(h):
    return blob_path(h).exists()


def blob_restore(h, dest):
    """dest gets the blob's bytes (copied, never linked); False when the blob is missing or damaged."""
    p = blob_path(h)
    try:
        b = p.read_bytes()
    except OSError:
        return False
    if sha(b) != h:
        return False
    atomic_write(dest, b)
    return True


# ---------------------------------------------------------------- locks
def _pid_alive(pid):
    if pid == os.getpid():
        return True
    if os.name == 'nt':
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return code.value == 259                        # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class Lock:
    """A lock file holding its owner's pid, taken over when that process is gone. acquire(block=False) -> bool.
    On Windows a lock file that one process is deleting while another still has it open (reading its pid) refuses a
    new exclusive create with EACCES (PermissionError), not EEXIST, for a moment (the cold run of 2026-10-07 lost a
    step to it): that counts as held. A refusal that lasts DENIED_MAX seconds is a real one and raises."""
    DENIED_MAX = 60.0

    def __init__(self, path):
        self.path = Path(path)
        self.denied = None                              # when the refusals began (time.monotonic)

    def acquire(self, block=True, poll=0.2):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self.denied = None
                return True
            except FileExistsError:
                self.denied = None
                try:
                    pid = int(self.path.read_text() or 0)
                except (OSError, ValueError):
                    pid = -1                            # being written: alive
                if pid >= 0 and not _pid_alive(pid):
                    try:
                        os.remove(self.path)
                    except OSError:
                        pass
                    continue
            except PermissionError:
                now = time.monotonic()
                if self.denied is None:
                    self.denied = now
                elif now - self.denied > self.DENIED_MAX:
                    raise
            if not block:
                return False
            time.sleep(poll)

    def release(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *a):
        self.release()


def free_commit():
    """Bytes of commit charge free (Windows; what a new process's memory is taken from), inf elsewhere."""
    if os.name != 'nt':
        return float('inf')
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + \
                   [(n, ctypes.c_ulonglong) for n in ('tp', 'ap', 'tf', 'af', 'tv', 'av', 'ae')]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.af


# ---------------------------------------------------------------- memos
def memo_file(name, key):
    return MEMO / name / key[:2] / f'{key}.pkl'


def memo_get(name, key):
    """(True, value) on a hit, else (False, None). Each hit unpickles a fresh copy and dates the entry anew (prune
    keeps what is used). Under refresh only an entry this run made (REFRESH_SINCE) is a hit."""
    if MODE == 'off':
        return False, None
    f = memo_file(name, key)
    try:
        if MODE == 'refresh' and f.stat().st_mtime < REFRESH_SINCE:
            return False, None
        v = pickle.loads(f.read_bytes())
    except (OSError, EOFError, pickle.UnpicklingError):
        return False, None
    if MODE == 'on':
        try:
            os.utime(f)
        except OSError:                                 # another process has it open: dated next time
            pass
    return True, v


def memo(name, parts, compute):
    """compute() once per key (parts), across processes: a process that asks for a key another one is computing
    waits for it and then reads it."""
    if MODE == 'off':
        return compute()
    key = digest([FORMAT, name, parts])
    hit, v = memo_get(name, key)
    if hit:
        return v
    with Lock(MEMO / name / 'locks' / f'{key}.lock'):
        hit, v = memo_get(name, key)
        if not hit:
            v = compute()
            atomic_write(memo_file(name, key), pickle.dumps(v, protocol=4))
    return v


def file_sig(p):
    st = Path(p).stat()
    return [st.st_size, st.st_mtime_ns]


def tree_stamp(root):
    """(relative path, size, mtime) of every file and folder under root: a folder's listing and every file's
    content (by its stat) in one hash. os.scandir: no file is opened."""
    h = hashlib.sha256()
    todo = [Path(root)]
    while todo:
        d = todo.pop()
        with os.scandir(d) as it:
            for e in sorted(it, key=lambda e: e.name):
                st = e.stat()
                h.update(f'{Path(e.path).relative_to(root).as_posix()}\0{st.st_size}\0{st.st_mtime_ns}\n'.encode())
                if e.is_dir():
                    todo.append(Path(e.path))
    return h.hexdigest()


def orca_signature(exe, profiles):
    """The OrcaSlicer install as the slicing depends on it: the executable's stat and every profile file's."""
    return {'exe': file_sig(exe), 'profiles': tree_stamp(profiles)}


# OrcaSlicer (2.4.0-dev CLI) cannot write a G-code whose full path is this many characters or more: it exits -100
# ("GCode processor post process export failed. Cannot open file for writing.") and leaves plate_1.gcode.tmp,
# although Windows long paths are on. Measured 2026-10-07 for a 3MF and an STL slice, in every folder shape, working
# folder and input depth tried: 243 works, 244 fails (Orca post-processes into <path>.tmp.postprocess: 244 + 16 =
# 260, MAX_PATH). pipeline.path_guard, slice_check.slice_part and configs_slice check it before Orca runs.
ORCA_PATH_MAX = 244


def orca_run(cmd, dest, inputs, exe, slots=2, timeout=600):
    """slice_check.slice_part's OrcaSlicer call, memoised: the key is the input files' bytes (the STL and the
    flattened presets), the command with those paths taken out, and the executable. A run that exits 0 and writes a
    G-code is stored (every file it wrote in dest); a failed one never is. At most `slots` OrcaSlicers run at once
    (across processes), each in a folder of its own (Orca writes its 00000.log in its working folder).
    -> an object with .returncode, .stdout, .stderr, as subprocess.run's."""
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    if MODE == 'off':
        return subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=flags)
    dest = Path(dest)
    names = {str(p): f'<in{i}>' for i, p in enumerate(inputs)}
    names[str(dest)] = '<dest>'

    def strip(a):
        for p, n in sorted(names.items(), key=lambda kv: -len(kv[0])):
            a = a.replace(p, n)
        return a
    parts = {'exe': file_sig(exe), 'inputs': [sha(Path(p).read_bytes()) for p in inputs], 'cmd': [strip(a) for a in cmd[1:]]}

    def run():
        before = {p.name: file_sig(p) for p in dest.iterdir() if p.is_file()}
        locks = [Lock(CACHE / 'run' / f'orca-{i}.lock') for i in range(slots)]     # kept: a lasting refusal raises
        while True:
            for i, slot in enumerate(locks):
                if slot.acquire(block=False):
                    break
            else:
                time.sleep(0.2)
                continue
            break
        try:
            cwd = CACHE / 'run' / f'orca-{i}'
            cwd.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=flags, cwd=cwd)
        finally:
            slot.release()
        files = {p.name: p.read_bytes() for p in dest.iterdir() if p.is_file() and before.get(p.name) != file_sig(p)}
        return {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr, 'files': files}

    key = digest([FORMAT, 'orca', parts])
    hit, v = memo_get('orca', key)
    if not hit:
        with Lock(MEMO / 'orca' / 'locks' / f'{key}.lock'):
            hit, v = memo_get('orca', key)
            if not hit:
                v = run()
                if v['returncode'] == 0 and any(n.endswith('.gcode') for n in v['files']):
                    atomic_write(memo_file('orca', key), pickle.dumps(v, protocol=4))
                return types.SimpleNamespace(returncode=v['returncode'], stdout=v['stdout'], stderr=v['stderr'])
    for n, b in v['files'].items():
        atomic_write(dest / n, b)
    return types.SimpleNamespace(returncode=v['returncode'], stdout=v['stdout'], stderr=v['stderr'])


# ---------------------------------------------------------------- CLI
def _size(d):
    return sum(f.stat().st_size for f in Path(d).rglob('*') if f.is_file()) if Path(d).exists() else 0


def stats():
    print(f'cache: {CACHE}')
    for d in ('blobs', 'steps', 'memo', 'logs'):
        p = (MEMO if d == 'memo' else CACHE / d)
        n = sum(1 for f in p.rglob('*') if f.is_file()) if p.exists() else 0
        print(f'  {d:6s} {n:6d} files {_size(p) / 1e6:9.1f} MB')
    for s in sorted((CACHE / 'steps').glob('*')) if (CACHE / 'steps').exists() else []:
        print(f"  {s.name:28s} {sum(1 for f in s.glob('*.json') if f.name != 'last.json')} entries")


def prune(keep=3, memo_days=MEMO_DAYS):
    """Keep the newest `keep` entries of each step, then drop the blobs no entry (and no last.json) refers to, and
    the memo entries (with any lock or temporary file left there) not made or served for memo_days days."""
    live = set()
    for s in (CACHE / 'steps').glob('*'):
        ents = sorted((f for f in s.glob('*.json') if f.name != 'last.json'), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in ents[keep:]:
            f.unlink()
        for f in ents[:keep]:
            e = json.loads(f.read_text())
            live |= {o['sha'] for o in e['outputs'].values()} | ({e['log']} if e.get('log') else set())
    n = 0
    for b in (CACHE / 'blobs').rglob('*'):
        if b.is_file() and b.name not in live:
            b.unlink()
            n += 1
    cut, nm, size = time.time() - memo_days * 86400, 0, 0
    for f in (MEMO.rglob('*') if MEMO.exists() else ()):
        try:
            st = f.stat()
            if f.is_file() and f.suffix in ('.pkl', '.lock', '.tmp') and st.st_mtime < cut:
                f.unlink()
                nm, size = nm + 1, size + st.st_size
        except OSError:                                 # in use: next time
            pass
    print(f'pruned to {keep} entries per step; {n} blobs removed; {nm} memo files unused for {memo_days} days '
          f'removed ({size / 1e6:.1f} MB)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    if cmd == 'stats':
        stats()
    elif cmd == 'prune':
        lock = Lock(CACHE / 'run' / 'pipeline.lock')     # pipeline.py's: never under a run that is storing entries
        if not lock.acquire(block=False):
            raise SystemExit(f'a pipeline.py runs in this checkout ({lock.path}): prune after it')
        try:
            prune(int(sys.argv[sys.argv.index('--keep') + 1]) if '--keep' in sys.argv else 3,
                  float(sys.argv[sys.argv.index('--memo-days') + 1]) if '--memo-days' in sys.argv else MEMO_DAYS)
        finally:
            lock.release()
    elif cmd == 'clear':
        shutil.rmtree(CACHE, ignore_errors=True)
        print(f'removed {CACHE}')
    else:
        raise SystemExit(__doc__)
