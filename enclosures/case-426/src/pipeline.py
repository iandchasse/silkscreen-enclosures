"""The whole 4.26 pipeline in one command, cached and in parallel (2026-10-06): every build (build.py's child), then
per build mechanics.py, dummy.py, plates.py and slice_check.py, then the shared-part and share checks, print/4.26/
and the cross-project check (build.py --finish), both plate files (../make_plates.py), and one OrcaSlicer project per
configuration (../make_plates.py configs -> out/configs/<slug>.3mf, then configs_slice.py slices and reads back each).

    python -B src/pipeline.py                     # all 32 configurations, every script, print/4.26/, the plate files
    python -B src/pipeline.py --builds six        # the six builds of before the variants (+ any print build not in them)
    python -B src/pipeline.py --builds print      # the print builds (print/4.26/ and the plate files are made from them)
    python -B src/pipeline.py --builds standard,chinless --steps build,mechanics
    python -B src/pipeline.py --quick             # iterate: the parts, and only the checks whose parts changed
    python -B src/pipeline.py --no-cache          # run every step again (and store what it makes)
    python -B src/pipeline.py --why               # each step that runs: what changed since its last run
    python -B src/pipeline.py --dry-run           # which steps would run, nothing run
    python -B src/pipeline.py --verify            # rerun the cached steps: each must give its files again
    python -B src/pipeline.py --unshared          # no shares: every build runs every check (the audit, with --verify)
    options: --cpu N (the CPU weights of the steps running at once; default the physical cores; --jobs N is its old
    name), --mem-floor GB (commit charge kept free, default 8), --blas default (OpenBLAS's own thread count instead
    of OPENBLAS_NUM_THREADS=1), --rehash (hash every file again), --prune N (after a run that passed, keep each
    step's N most recently used cache entries, and the memo entries they name or that were used in the last
    cache.MEMO_DAYS days; default 3, 0: never), --configs no (no per-configuration projects),
    -- <args for the builds>
    build.py with no variant (its default and --only) runs its builds through here too.

--builds takes slugs (variants.py: <base>[-leftkeys|-rightkeys|-upperkeys][-nodev]) and the presets all (the 32,
the default), six and print, comma-separated, in any mix. A build's twins (variants.twins: the same configuration
with one axis at its default) come into the run too, as builds only, because its checks compare with them (a chinless
build's chin_check, the share checks; cross_reads): a check whose twin is not built fails, it is never skipped. So
--builds light-strip-chinless-upperkeys-nodev builds up to 12 configurations; the presets bring in nothing more.
Time, all 32: 58 min cold (--no-cache, 2026-10-10, the defaults: --cpu 12, the shares, OPENBLAS_NUM_THREADS=1, 18.7 GB
of commit charge free at the start; the steps' processes at most 6.7 GB of private memory together), against 2 h 12
min before the scheduler and the shares (6 jobs, 2026-10-07; 20.7 GB). Warm (nothing changed): 78-79 s (2026-10-10):
the 192 cached steps are restored in about 10 s, then the five uncached steps (finish-default 15 s, plates3mf 8,
finish-only 9, configs 17, configs-slice 22) run mostly one after another. The six (--builds six): 22-27 min cold at
the old 6 jobs (2026-10-07).
OrcaSlicer cannot write a G-code whose path is 244 characters or more (it exits -100): a run that slices checks the
longest out/<build>/slice/<part>/plate_1.gcode and out/configs/slice/<slug>/plate_2.gcode paths before it starts,
and stops with the checkout's path to shorten.

The step cache (cache.py). A step is one script process for one build, exactly as before (the same code, in the
same order, on the same inputs: each process starts clean, and every one was shown deterministic), so a step
whose key is in the cache is not run: its files are restored, byte for byte. Its key holds everything it reads:
  the source of every src/ module it imports (its closure; params.py is one, so any params edit reruns it), the
  hardware/ files, the build and its arguments, the interpreter and every installed package, the project's path,
  and the files it reads from the steps before it (a build's parts for mechanics, dummy, plates; plates' files
  for slice_check, with the OrcaSlicer install). A STEP counts without its export time.
Each step runs under _step.py, which records every file it reads and writes: a read outside its key or a write
outside its own files fails the run and nothing is stored, so an input cannot be forgotten silently. A step is
stored only when it exited 0. Restoring never trusts the disk: a file that differs from the entry is copied back.
An entry's file date is when it was last made or served (a restore touches it), so `cache.py prune --keep N` keeps
each step's N most recently used runs, and --why and --quick compare with the run the disk holds.
An entry also names the memo files its run read or made ('memos': a slice step's OrcaSlicer runs and the preset
index; _step.py records the memo folder also where SILKSCREEN_MEMO or SILKSCREEN_CACHE puts it outside the checkout).
Finding the entry dates them anew, and so does the prune after a run, for every entry it keeps (keep_memos), so the
memo prune (by age) never drops a G-code that a kept entry would replay under --verify (a real OrcaSlicer run writes
a new G-code each time: its header has the time). `cache.py prune` by hand goes by the memos' dates alone: an entry
whose memos it removed is logged as such when it is next found, and its build needs a --no-cache run before a
--verify (a --verify would slice again, fail, and store new memos under the same names).
The cheap steps (build.py --finish, ../make_plates.py: 8-30 s each) always run: they read case-368 and print/. So do
the per-configuration projects (configs: make_plates.py configs for the builds asked for, about 1 s each, once their
builds, plates and share checks have passed; configs-slice: configs_slice.py, whose OrcaSlicer runs are memoised by
each file's bytes): make_plates.py lives outside src/ and reads the installed Orca profiles, so a key would miss them.
Inside the steps a memo skips work across builds: OrcaSlicer (cache.orca_run).

Parallel (the scheduler, 2026-10-08): a step that starts a process waits for the steps whose files it reads (a
build's mechanics, dummy, plates and slice_check for its parts: build_all; its checks only add JSON reports), then for
the Scheduler: the CPU weights of the running steps stay within --cpu (WEIGHT; default the physical cores, where
throughput levels off: 6 -> 12 steps gives about 1.5 x), and free commit charge minus what the running steps may still
take minus its own estimate stays above --mem-floor + 0.5 GB (a step that would run alone: above --mem-floor; while
other programs leave less, it waits). Estimates are each step's own measured peaks (every step runs in a job object,
jobs.py: its peak commit and CPU time, in its cache entry and out/.cache/stats.json, written as each step passes, so
a killed run keeps them; a failed step or a --quick build records nothing), else its family's, else PEAK_GB (at least the
2026-10-10 cold run's peaks; a mechanics step's own runs count only those of the same script, mechanics.py or
mechanics_share.py; an uncached step, whose cost depends on its memos, never under PEAK_GB). The guard steps start
first (each is short; a build that reaches a shared check before the guards have passed runs the check itself, and
a mechanics step that may share waits for them), then the longest remaining chain (b-level); behind a head that does
not fit, only short steps may start. A safety valve ends and requeues the youngest
of our own sheddable steps that still holds memory if commit charge stays under the floor for 20 s (other programs
grew: the cold run of 2026-10-10 went to 7.5 GB free for a minute while they held 5 GB more than at its start); it
never touches another process. The scheduler changes only start times: no input, argument or environment of a step,
so no file. OPENBLAS_NUM_THREADS=1 (--blas one, the default) does change every step's environment: it cuts each
step's commit to about a quarter (OpenBLAS commits buffers for every thread at import), and it is set in this
process's environment before any key, so the keys hold it.

Shares (2026-10-08): a check whose inputs are the same as another build's runs once. guard.py (a cached step per
build, after its parts) writes out/.share/<build>.json: the STL triangles within the regions each shared check
reads, the BREP regions it crops (face signatures), the hardware there, and every params value its code can reach
(deps.py). Some regions are read from the checks' code and checked at each run; others are copied numbers, so after
editing a shared check's code run --unshared --verify once.
strip and bottom_keys: the build child asks when it reaches the check (build._shared_from); the first ancestor build
in the run (its slug with non-default axes set back) with the same guard digest is the source: the child leaves the
check out, and this runner copies that build's report once both have ended, before storing the build, whose entry is
then the same as if it had run the check. mechanics: the print builds run mechanics.py; another build whose side-key
and key-slot guards match theirs runs mechanics_share.py (the slow entries from them, the rest computed). Leaving a
check out changes no other file of the build (compared), and every shared report is byte-identical to the one the
build would make (all 32 compared). --unshared runs everything in every build; with --verify it is the audit: each
build reruns every check and must give its cache entry's files (the shared reports among them: a build's key is the
same shared or not), and each mechanics.json that mechanics.py makes for a build whose mechanics the shares compose
must be the composed one, byte for byte (audit_mech: the entries mechanics_share.py made from the same parts, code,
environment and owners' files; a build that has none is listed as not audited).

--quick: the builds write their parts as always (the same bytes), then run only the checks that read a part that
differs from the last full run's (CHECK_PARTS; every check when build.py, mechanics.py or the
hardware changed, or --checks a,b to name them: build.CHECKS). A quick build is never stored and is listed in
out/.cache/quick.json until a full run; its reports can differ in a last digit from a full run's (a check sees what
the checks before it did to the shapes), its parts and everything made from them cannot. print/ is not written.
"""
import fnmatch, json, os, subprocess, sys, threading, time
from pathlib import Path
import cache
import jobs                                         # job objects: the scheduler's measurements (runner only)
import variants                                     # the slugs (standard library only: no params, no out/)

ROOT, SRC, OUT, CACHE = cache.ROOT, cache.SRC, cache.ROOT / 'out', cache.CACHE
ENCL = ROOT.parent
ALL_BUILDS = variants.ALL                           # the 32 configurations
PRINT_BUILDS = variants.PRINT_BUILDS
# --builds presets. 'six' is the six builds of before the variants plus any print build not among them, so a quick
# run of it always makes print/4.26/ and the plate file (finish-default needs every print build)
PRESETS = {'all': ALL_BUILDS, 'print': PRINT_BUILDS,
           'six': (*variants.SIX, *(b for b in PRINT_BUILDS if b not in variants.SIX))}
KINDS = ('build', 'mechanics', 'dummy', 'plates', 'slice')
SCRIPT = {'build': 'build.py', 'mechanics': 'mechanics.py', 'dummy': 'dummy.py', 'plates': 'plates.py',
          'slice': 'slice_check.py', 'guard': 'guard.py'}
NOT_CODE = {'pipeline', '_step', 'jobs'}            # the runner: in no step's computation
# Shares (2026-10-08; guard.py, mechanics_share.py): a check whose inputs are the same as another build's is run once.
# strip and bottom_keys: a build's candidates are its ancestors in the run (its slug with any of its non-default axes
# set to the default) that have the check; when the build child reaches the check it asks, and the first candidate
# whose guard digest equals its own is the one it takes the report from (the pipeline copies the file once both have
# ended, before the build is stored: its cache entry is the same either way). mechanics: the print builds run
# mechanics.py; any other build whose guard matches one of theirs (same chin) runs mechanics_share.py.
SHARE_REPORTS = {'bottom_keys': 'bottom-keys.json', 'strip': 'light-strip.json'}
SHARE_HAS = {'bottom_keys': lambda c: c.bottom_keys, 'strip': lambda c: c.panel == 'light-strip'}
MECH_OWNERS = tuple(b for b in variants.ORDER if b in variants.PRINT_BUILDS)
GUARDS = OUT / '.share'                             # guard.py: out/.share/<build>.json
# out/<build>/ files that are not the build child's
OTHERS = {'mechanics.json', 'pcba-dummy.stl', 'pcba-dummy.json', 'shared.json', 'gate-print.step', 'build.log'}
# a step's priority: its build's place in variants.ORDER (the longest first) + PRIORITY_STRIDE x its kind's index. The
# scheduler's order is (guard steps first, the longest remaining chain: b-level, then this), so it only breaks ties;
# plan() also sorts the steps by it
PRIORITY = {b: i for i, b in enumerate(variants.ORDER)}
PRIORITY_STRIDE = 100
assert PRIORITY_STRIDE > len(PRIORITY)
# the slice step's longest output path under out/<build>/ (slice_check: out/<build>/slice/<part>/plate_1.gcode; the
# longest part name, the coupons'), checked against cache.ORCA_PATH_MAX before a run starts
SLICE_LONGEST = Path('slice') / 'coupon-chin' / 'plate_1.gcode'
CONFIGS_SLICE = OUT / 'configs' / 'slice'           # configs_slice.py: <slug>/plate_<n>.gcode, 2 plates at most
# --quick: the parts each check reads (fnmatch on the part files' stems)
CHECK_PARTS = {'insertion': ('tub', 'midplate', 'ref_*'),
               'moves': ('tub', 'midplate', 'lid', 'lid_body', 'skey_*', 'ref_*'),
               'lid_close': ('tub', 'midplate', 'lid_body'),
               'interference': ('*',),
               'bottom_keys': ('tub', 'midplate', 'lid', 'lid_body', 'key*', 'crank*', 'gate', 'coupon-*', 'ref_rod'),
               'strip': ('tub', 'midplate', 'lid', 'lid_body', 'skey_*', 'ref_*'),
               'chin': ('tub', 'lid', 'lid_body'),
               'header': ('tub', 'lid', 'lid_body'),
               'sides': ('tub', 'lid', 'lid_body', 'skey_*'),
               'community': ('tub', 'lid', 'midplate', 'inlay_*')}


def cross_reads(build):
    """[(other build, files)] that a build child reads from another build's folder (found by _step.py's audit):
    build.chin_check compares a chinless build's tub and lid with its keyed twin's (variants.twin(build, 'chin')), and
    a side-key layout's are compared with its all-keys twin's (the sides check). Those twins are always in the run
    (plan pulls them in), and the build waits for their parts (it reads them at its end anyway, as it always did)."""
    c = variants.parse(build)
    out = []
    if not c.bottom_keys:
        out.append((variants.twin(build, 'chin'), ('tub.step', 'lid.step')))
    if c.sides != 'all':
        out.append((variants.twin(build, 'sides'), ('tub.step', 'lid.step')))
    return out


def expand(spec):
    """--builds: comma-separated slugs and presets -> the builds, each once, in PRIORITY order. Nothing named (an
    empty --builds) is an error, not an empty run."""
    out = set()
    for tok in (t.strip() for t in spec.split(',')):
        if not tok:
            continue
        if tok in PRESETS:
            out |= set(PRESETS[tok])
            continue
        try:
            variants.parse(tok)
        except ValueError as ex:
            raise SystemExit(f'--builds: {ex} (or a preset: {", ".join(PRESETS)})')
        out.add(tok)
    if not out:
        raise SystemExit(f'--builds {spec!r} names no configuration (slugs, or a preset: {", ".join(PRESETS)})')
    return sorted(out, key=PRIORITY.get)


def ancestors(slug):
    """The configurations a slug becomes when any of its non-default axes go back to the default (its twins, theirs,
    to the default configuration): the builds it may take a shared check's report from."""
    a = variants.axes(slug)
    nd = [x for x in variants.AXES if a[x] != variants.DEFAULT[x]]
    out = set()
    for mask in range(1, 1 << len(nd)):
        b = dict(a)
        for i, x in enumerate(nd):
            if mask >> i & 1:
                b[x] = variants.DEFAULT[x]
        out.add(variants.make(b['panel'], b['chin'], b['sides'], b['dev']))
    return out


def with_twins(builds):
    """The builds a run of these needs: each one's twins (variants.twins: its share checks compare with all of them)
    and, for every build in the run, the twins its own build step reads (cross_reads), to the end."""
    need = set(builds)
    for b in builds:
        need |= {t for _, t in variants.twins(b)}
    todo = list(need)
    while todo:
        b = todo.pop()
        for t, _ in cross_reads(b):
            if t not in need:
                need.add(t)
                todo.append(t)
    return sorted(need, key=PRIORITY.get)


CHECKS = ('insertion', 'moves', 'lid_close', 'interference', 'bottom_keys', 'strip', 'chin', 'header', 'sides', 'community')   # = build.CHECKS
CHECK_CODE = ('build', 'lid_close', 'mechanics', 'refs', 'panel', 'hw', 'community')   # a change here: every check (--quick)


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


free_commit = cache.free_commit
STATS = CACHE / 'stats.json'        # {step id: its last 5 runs: at, wall_s, cpu_s, peak_gb, blas, family, script, phase1_s}


def load_stats():
    try:
        return json.loads(STATS.read_text())
    except (OSError, ValueError):
        return {}


def memos_of(audit):
    """The memo files (cache.MEMO-relative, '/'-separated) a step's process read or made, from its _step.py audit:
    a slice step's OrcaSlicer runs and the preset index. The audit records the memo folder wherever it is (also a
    SILKSCREEN_MEMO or SILKSCREEN_CACHE outside the checkout)."""
    m = os.path.normcase(str(cache.MEMO)) + os.sep
    return sorted({p[len(m):].replace(os.sep, '/') for p in audit['reads'] + audit['writes']
                   if p.startswith(m) and p.endswith('.pkl')})


def date_memos(names):
    """Date these memo files now (cache.prune drops a memo not made or used for cache.MEMO_DAYS). -> the ones gone."""
    gone = []
    for n in names:
        try:
            os.utime(cache.MEMO / n)
        except FileNotFoundError:
            gone.append(n)
        except OSError:                                 # another process has it open: dated next time
            pass
    return gone


def keep_memos(keep):
    """Before cache.prune(keep): date the memo files named by the entries it keeps (each step's `keep` most recently
    used, its rule), so a memo lasts as long as an entry that replays it, also for the steps this run did not have."""
    for s in (CACHE / 'steps').glob('*'):
        ents = sorted((f for f in s.glob('*.json') if f.name != 'last.json'), key=lambda f: f.stat().st_mtime,
                      reverse=True)
        for f in ents[:keep]:
            try:
                date_memos(json.loads(f.read_text()).get('memos', ()))
            except (OSError, ValueError):
                pass


def stat_sig(path):
    try:
        st = Path(path).stat()
        return (st.st_size, st.st_mtime_ns)
    except OSError:
        return None


class Hasher:
    """sha256 of files (raw, and masked: a STEP without its export time), remembered by (size, mtime) in stat.json
    for big files only (the parts and board.step): a file under BIG (the code, the hardware JSON) is always read, so an
    edit that keeps its size and mtime is still seen."""
    BIG = 2 << 20

    def __init__(self, rehash):
        self.f = CACHE / 'stat.json'
        self.lock = threading.Lock()
        try:
            self.memo = {} if rehash else json.loads(self.f.read_text())
        except (OSError, ValueError):
            self.memo = {}

    def get(self, path):
        path = Path(path)
        st = path.stat()
        k = str(path)
        with self.lock:
            r = self.memo.get(k)
        if r and r[0] == st.st_size and r[1] == st.st_mtime_ns and st.st_size >= self.BIG:
            return r[2], r[3]
        b = path.read_bytes()
        raw = cache.sha(b)
        m = cache.sha(cache.masked(path, b)) if path.suffix.lower() in ('.step', '.stp') else raw
        with self.lock:
            self.memo[k] = [st.st_size, st.st_mtime_ns, raw, m]
        return raw, m

    def seen(self, path):
        """(size, mtime_ns) of path when it was last hashed here (else as it is now; None if it is not there)."""
        with self.lock:
            r = self.memo.get(str(Path(path)))
        return (r[0], r[1]) if r else stat_sig(path)

    def known(self, path, raw, m):
        st = Path(path).stat()
        with self.lock:
            self.memo[str(path)] = [st.st_size, st.st_mtime_ns, raw, m]

    def save(self):
        with self.lock:
            cache.atomic_write(self.f, json.dumps(self.memo).encode())


class Shed(Exception):
    """The safety valve ended this step's job (commit charge ran low): it is run again from scratch."""


class Scheduler:
    """Every step that starts a process is admitted here (2026-10-08), in Pipeline.order_key's order (the guard
    steps, then b-level: Pipeline.prepare), when
      CPU     the CPU weights of the running steps + its own <= cap (WEIGHT; cap: --cpu, default the physical cores)
      memory  free commit charge - what the running steps may still take (their estimates - what they hold now, read
              at most FRESH_S before) - its own estimate >= floor + MARGIN_GB (free commit is read live: other
              programs count)
    or, when none of ours runs, when free commit - its own estimate >= floor (no margin and no CPU cap: alone it may
    take the whole budget, never the floor; it waits while other programs hold more, else the valve would end it and
    it would be admitted again at once, a loop of restarts, 2026-10-10). A step that waits behind a head that does
    not fit may start only when it is short (estimated <= BACKFILL_S) and fits. The safety valve: free commit under
    the floor for VALVE_S seconds (our own steps stay above floor + MARGIN_GB by the admission rule, so only other
    programs' growth or a step past its estimate gets it there) ends the youngest of OUR running steps that nothing
    waits on (SHEDDABLE, or a build before its parts are written) and that still holds memory, and queues it again,
    at most one per 30 s; it is never another program. Only start times change: no step's inputs, arguments or
    environment, so no output can (each step is its own process)."""
    MARGIN_GB, VALVE_S, BACKFILL_S, POLL_S, FRESH_S = 0.5, 20.0, 120.0, 2.0, 0.5

    def __init__(self, cpu, floor_gb, pipe):
        self.cpu, self.floor, self.P = cpu, floor_gb, pipe
        self.valve_gb = floor_gb                        # the valve opens under the floor (was 6 GB until 2026-10-10)
        self.cv = threading.Condition()
        self.waiting = []                               # [(order key, seq, step)]
        self.running = {}                               # step -> {'job', 'est', 'w', 'cur', 'peak', 'at'}
        self.seq = 0
        self.low_since = None
        self.last_shed = 0.0
        self.sampled = 0.0
        self.stop = threading.Event()
        self.mon = threading.Thread(target=self.monitor, daemon=True)
        self.mon.start()

    def free_gb(self):
        return free_commit() / 1e9

    def owed(self):
        return sum(max(0.0, r['est'] - r['cur']) for r in self.running.values())

    def cpu_used(self):
        return sum(r['w'] for r in self.running.values())

    @staticmethod
    def sample(recs):
        """Each running step's commit now (its job's processes; 0 once they have ended) and its peak so far."""
        for r in recs:
            if r['job'] is not None:
                try:
                    r['cur'] = r['job'].commit() / 1e9
                    r['peak'] = max(r['peak'], r['cur'])
                except OSError:
                    pass

    def fits(self, est, w):
        if not self.running:                            # alone: the floor still holds (was free - est >= 2 GB)
            return self.free_gb() - est >= self.floor
        return (self.cpu_used() + w <= self.cpu + 1e-9
                and self.free_gb() - self.owed() - est >= self.floor + self.MARGIN_GB)

    def admit(self):
        """(under cv) start what fits, in order; behind a head that does not fit only short steps. What the running
        steps hold is read again first (at most every FRESH_S), so it is as fresh as the free commit it is set
        against (the monitor's reading can be POLL_S old)."""
        if time.time() - self.sampled > self.FRESH_S:
            self.sample(list(self.running.values()))
            self.sampled = time.time()
        blocked = False
        for item in sorted(self.waiting):
            s = item[2]
            if s.admitted:
                continue
            est, w = self.P.est_peak(s), WEIGHT.get(s.kind, 1.0)
            if blocked and self.P.est_wall(s) > self.BACKFILL_S:
                continue
            if self.fits(est, w):
                s.admitted = True
                s.admit_note = (f'est {est:.1f} GB, free {self.free_gb():.1f} GB, '
                                f'cpu {self.cpu_used() + w:g}/{self.cpu:g}')
                self.running[s] = {'job': None, 'est': est, 'w': w, 'cur': 0.0, 'peak': 0.0, 'at': time.time()}
            else:
                blocked = True

    def acquire(self, step):
        with self.cv:
            self.seq += 1
            step.admitted = False
            item = (self.P.order_key(step), self.seq, step)
            self.waiting.append(item)
            warned = time.time()
            while True:
                self.admit()
                if step.admitted:
                    break
                if time.time() - warned > 300:
                    log(f'{step.id}: waiting (free commit {self.free_gb():.1f} GB, owed {self.owed():.1f}, '
                        f'cpu {self.cpu_used():g}/{self.cpu:g})' + ('' if self.running else
                        f': none of ours runs, and other programs leave less than the floor ({self.floor:g} GB) + '
                        f'its estimate ({self.P.est_peak(step):.1f} GB); it starts when they free some, or with a lower '
                        f'--mem-floor'))
                    warned = time.time()
                self.cv.wait(self.POLL_S)
            self.waiting.remove(item)
            self.cv.notify_all()

    def attach(self, step, job):
        with self.cv:
            if step in self.running:
                self.running[step]['job'] = job

    def release(self, step):
        with self.cv:
            r = self.running.pop(step, None)
            self.cv.notify_all()
        return r

    def monitor(self):
        while not self.stop.wait(self.POLL_S):
            with self.cv:
                recs = list(self.running.values())
            self.sample(recs)
            free = self.free_gb()
            now = time.time()
            if free >= self.valve_gb:
                self.low_since = None
            elif self.low_since is None:
                self.low_since = now
            elif now - self.low_since >= self.VALVE_S and now - self.last_shed > 30:
                self.shed(free)
            with self.cv:
                self.cv.notify_all()

    def shed(self, free):
        """End the youngest of our sheddable steps whose processes still hold memory (one that holds none, its
        process ended and its files being stored, would free nothing)."""
        with self.cv:
            cands = [(r['at'], s) for s, r in self.running.items()
                     if r['job'] is not None and r['cur'] > 0.0 and self.P.sheddable(s)]
        if not cands:
            return
        s = max(cands, key=lambda x: x[0])[1]
        r = self.running.get(s)
        s.shed = True
        s.shed_peak = r['peak'] if r else 0.0
        self.last_shed = time.time()
        log(f'{s.id}: SHED by the safety valve (commit charge free {free:.1f} GB < {self.valve_gb:g} for '
            f'{self.VALVE_S:g} s): its job is ended and it runs again from scratch later')
        try:
            r['job'].terminate()
        except (OSError, AttributeError, TypeError):
            pass


# CPU weight per step kind: a slice step waits on OrcaSlicer's two slots much of the time (CPU/wall 0.4-0.9), the
# small steps are short; a guard step imports two STEP files and crops them
WEIGHT = {'build': 1.0, 'mechanics': 1.0, 'dummy': 1.0, 'guard': 1.0, 'finish-default': 1.0, 'finish-only': 1.0,
          'slice': 0.5, 'configs-slice': 0.5, 'plates': 0.5, 'plates3mf': 0.5, 'configs': 0.5}
SHEDDABLE = {'mechanics', 'dummy', 'slice', 'configs-slice', 'guard'}
# peak commit (GB) of one step's job when there is no measurement of it yet, by OpenBLAS mode (pipeline --blas):
# 'default' from the 2026-10-07/08 cold runs' fits (+ the largest residual), 'one' measured with
# OPENBLAS_NUM_THREADS=1 (2026-10-08: the chinless build, its mechanics.py and dummy.py, each in a job object) with a
# margin for what was not measured, raised to at least
# 1.1 x the largest peak of the 2026-10-10 cold run + 0.1 (est_peak's own rule): build 1.26 GB (light-strip-rightkeys),
# mechanics 0.86 (mechanics.py of light-strip), guard 0.50, dummy 0.50; it had admitted the builds at 0.9
PEAK_GB = {'default': {'build': 2.4, 'mechanics': 2.7, 'dummy': 2.2, 'plates': 1.8, 'slice': 2.0, 'guard': 2.0,
                       'finish-default': 2.2, 'finish-only': 2.2, 'plates3mf': 1.9, 'configs': 1.4, 'configs-slice': 2.0},
           'one': {'build': 1.5, 'mechanics': 1.05, 'dummy': 0.65, 'plates': 0.6, 'slice': 1.2, 'guard': 0.65,
                   'finish-default': 1.0, 'finish-only': 1.0, 'plates3mf': 0.6, 'configs': 0.6, 'configs-slice': 1.2}}
# a step's duration when it has no measurement yet (s; the 2026-10-07 cold run's family means): for the b-level
WALL_S = {('build', 'light-strip'): 1750, ('build', 'standard'): 1200, ('build', 'light-strip-chinless'): 850,
          ('build', 'chinless'): 400, ('mechanics', True): 500, ('mechanics', False): 75, 'dummy': 45, 'plates': 8,
          ('slice', True): 130, ('slice', False): 60, 'guard': 30, 'finish-default': 30, 'finish-only': 30,
          'plates3mf': 10, 'configs': 25, 'configs-slice': 25}


class Failed(Exception):
    pass


class Step:
    def __init__(self, kind, build=None, args=(), cached=True, prio=9):
        self.kind, self.build, self.args, self.cached, self.prio = kind, build, list(args), cached, prio
        self.id = f'{kind}:{build}' if build else kind
        self.deps = []                              # (step, 'phase1' | 'done')
        self.phase1_ev, self.done_ev = threading.Event(), threading.Event()
        self.ok = None
        self.admitted, self.admit_note, self.shed, self.shed_peak = False, '', False, 0.0
        self.blevel, self.job_stats, self.phase1_s = 0.0, {}, None
        self.phase1 = {}                            # rel -> masked sha: a build's parts (build_all)
        self.outputs = {}                           # rel -> raw sha, after it ran or was restored
        self.status, self.t0, self.t1 = 'waiting', None, None
        self.quick = None                           # --quick: the checks ('auto' or a list)
        self.reads = []                             # (rel path, the step that makes it or None): other builds' files
        self.script = SCRIPT.get(kind)              # mechanics: mechanics_share.py when it takes a share
        self.soft = set()                           # deps whose failure does not fail this step (share candidates)
        self.share_cands = {}                       # build: {check: [candidate builds]} (SHARE_REPORTS)
        self.shared = {}                            # build: {check: the build its report is taken from}
        self.mech_cands = []                        # mechanics: the print builds it may take entries from
        self.share_note = ''
        self.parts = None                           # its key's parts, once made (audit_mech)

    @property
    def dir(self):
        return OUT / self.build if self.build else OUT

    def scope(self):
        """{rel: (size, mtime)} of the files this step owns (writes) as they are now."""
        d = self.dir
        if self.kind == 'build':
            files = [f for f in d.iterdir() if f.is_file() and f.name not in OTHERS] if d.exists() else []
        elif self.kind == 'guard':
            files = [GUARDS / f'{self.build}.json']
        elif self.kind == 'mechanics':
            files = [d / 'mechanics.json']
        elif self.kind == 'dummy':
            files = [d / 'pcba-dummy.stl', d / 'pcba-dummy.json']
        elif self.kind in ('plates', 'slice'):
            sub = d / ('print' if self.kind == 'plates' else 'slice')
            files = [f for f in sub.rglob('*') if f.is_file()] if sub.exists() else []
        else:
            return {}
        out = {}
        for f in files:
            try:
                st = f.stat()
            except FileNotFoundError:
                continue
            out[rel(f)] = (st.st_size, st.st_mtime_ns)
        return out

    def in_scope(self, path):
        """Whether a (normcased absolute) path is one of this step's own files."""
        d = os.path.normcase(str(self.dir))
        if self.kind == 'build':
            return os.path.dirname(path) == d and os.path.basename(path) not in {os.path.normcase(x) for x in OTHERS}
        if self.kind == 'mechanics':
            return path == os.path.normcase(str(self.dir / 'mechanics.json'))
        if self.kind == 'guard':
            return path == os.path.normcase(str(GUARDS / f'{self.build}.json'))
        if self.kind == 'dummy':
            return path in {os.path.normcase(str(self.dir / n)) for n in ('pcba-dummy.stl', 'pcba-dummy.json')}
        if self.kind in ('plates', 'slice'):
            sub = os.path.normcase(str(self.dir / ('print' if self.kind == 'plates' else 'slice')))
            return path.startswith(sub + os.sep)
        return False


class Pipeline:
    def __init__(self, opts):
        self.o = opts
        self.since = time.time()                        # --no-cache: memos made after this are this run's
        self.hasher = Hasher(opts.rehash)
        self.blas = 'one' if os.environ.get('OPENBLAS_NUM_THREADS') == '1' else 'default'
        self.stats = load_stats()
        self.sched = None                               # go(): the Scheduler
        self.steps = []
        self.failed = []
        self.verified = []
        self.lock = threading.Lock()
        self._static = None
        self._orca = None
        self.by = {}                                    # (kind, build) -> Step (plan)
        self.guards = {}                                # build -> its guard.py JSON, once read

    # ---------------------------------------------------------------- scheduling (no key reads any of this)
    def family(self, step):
        return (step.kind, variants.parse(step.build).base if step.build else None)

    def est_peak(self, step):
        """GB of commit charge the step's job may reach: 1.1 x the largest of its last 3 measured peaks (same OpenBLAS
        mode, same script: a composed mechanics.json costs less than mechanics.py's) + 0.1; else 1.1 x its family's
        largest (kind, base); else PEAK_GB; raised to what a shed run held. An uncached step (finish, plates3mf,
        configs, configs-slice) costs what its memos leave to do (a warm configs-slice holds 0.07 GB, a cold one
        0.8): never under PEAK_GB."""
        script = step.script or step.kind
        runs = [r['peak_gb'] for r in self.stats.get(step.id, [])
                if r.get('blas') == self.blas and r.get('peak_gb') and r.get('script', script) == script]
        if runs:
            est = 1.1 * max(runs[-3:]) + 0.1
        else:
            fam = self.family(step)
            ps = [r['peak_gb'] for rs in self.stats.copy().values() for r in rs[-3:]   # copy: note_stats adds ids
                  if r.get('blas') == self.blas and r.get('peak_gb') and tuple(r.get('family') or ()) == fam]
            est = 1.1 * max(ps) + 0.1 if ps else PEAK_GB[self.blas].get(step.kind, 2.0)
        if not step.cached:
            est = max(est, PEAK_GB[self.blas].get(step.kind, 2.0))
        return max(est, step.shed_peak * 1.1)

    def est_wall(self, step):
        rs = [r['wall_s'] for r in self.stats.get(step.id, []) if r.get('wall_s')]
        if rs:
            return rs[-1]
        fam = self.family(step)
        ws = [r['wall_s'] for rs_ in self.stats.copy().values() for r in rs_[-1:]
              if r.get('wall_s') and tuple(r.get('family') or ()) == fam]
        if ws:
            return sum(ws) / len(ws)
        if step.build:
            c = variants.parse(step.build)
            for k in ((step.kind, c.base), (step.kind, c.bottom_keys)):
                if k in WALL_S:
                    return WALL_S[k]
        return WALL_S.get(step.kind, 60)

    def est_phase1(self, step):
        rs = [r['phase1_s'] for r in self.stats.get(step.id, []) if r.get('phase1_s')]
        return rs[-1] if rs else 0.3 * self.est_wall(step)

    def prepare(self):
        """Each step's b-level: its estimated duration + the longest b-level of what waits on it (a build's phase-1
        dependants count from its phase-1 time): the scheduler starts the longest remaining chain first."""
        after = {s: [] for s in self.steps}
        for s in self.steps:
            for d, what in s.deps:
                if d in after:
                    after[d].append((s, what))
        memo = {}

        def b(s):
            if s not in memo:
                memo[s] = 0.0                           # (no cycles; a guard against one)
                dur, best = self.est_wall(s), self.est_wall(s)
                for s2, what in after[s]:
                    best = max(best, (self.est_phase1(s) if what == 'phase1' else dur) + b(s2))
                memo[s] = best
            return memo[s]
        for s in self.steps:
            s.blevel = b(s)

    def order_key(self, step):
        return (0 if step.kind == 'guard' else 1, -round(step.blevel, 1), step.prio)

    def sheddable(self, step):
        """The safety valve may end it: nothing that waits on it has started (a build only before build_all ends)."""
        if step.kind == 'build':
            return not step.phase1_ev.is_set()
        return step.kind in SHEDDABLE

    def note_stats(self, step, wall):
        """A passed step's measurements, written to stats.json at once (2026-10-10: a pipeline that is killed kept
        none, so the next run admitted every step at PEAK_GB). A --quick build is not a full run: not recorded."""
        if step.quick is not None:
            return
        st = dict(step.job_stats)
        rec = {'at': time.strftime('%Y-%m-%d %H:%M:%S'), 'wall_s': round(wall, 1), 'blas': self.blas,
               'family': list(self.family(step)), 'script': step.script or step.kind,
               **{k: st[k] for k in ('peak_gb', 'cpu_s') if k in st}}
        if step.phase1_s:
            rec['phase1_s'] = round(step.phase1_s, 1)
        with self.lock:
            self.stats[step.id] = (self.stats.get(step.id, []) + [rec])[-5:]
            try:
                cache.atomic_write(STATS, json.dumps(self.stats, indent=1).encode())
            except OSError as ex:
                log(f'{step.id}: stats.json not written ({ex}); go() writes it at the end')

    # ---------------------------------------------------------------- keys
    def static(self):
        if self._static is None:
            hwd = ROOT / 'hardware'
            files = sorted(f for f in hwd.rglob('*') if f.is_file() and f.name not in cache.HW_SKIP)
            self.hw_files = {os.path.normcase(str(f)) for f in files}
            self._static = {'format': cache.FORMAT, 'root': str(ROOT), 'env': cache.env_fingerprint(),
                            'hardware': cache.digest({rel(f): self.hasher.get(f)[0] for f in files})}
            self.hw_stats = {str(f): self.hasher.seen(f) for f in files}
        return self._static

    def orca(self):
        """The OrcaSlicer install's signature (cache.orca_signature), at the paths slice_check.py names."""
        if self._orca is None:
            import re
            t = (SRC / 'slice_check.py').read_text(encoding='utf-8')
            exe, prof = (Path(re.search(rf"^{n} = Path\(r'([^']+)'\)", t, re.M).group(1)) for n in ('ORCA', 'PROFILES'))
            self._orca = cache.orca_signature(exe, prof)
        return self._orca

    def sources(self, step):
        script = Path(step.script or 'build.py').stem
        mods = [m for m in cache.closure(script) if m not in NOT_CODE]
        return {m: self.hasher.get(SRC / f'{m}.py')[0] for m in mods}

    def upstream(self, step):
        """{rel: masked sha} of the files this step reads from the steps before it."""
        up = {}
        for d, _ in step.deps:
            if d.kind == 'build' and d.build == step.build:
                up.update(d.phase1)
            elif d.kind in ('dummy', 'plates'):
                up.update({r: self.hasher.get(ROOT / r)[1] for r in d.outputs})
        for r, maker in step.reads:
            if maker is not None and maker.kind == 'build':
                up[r] = maker.phase1.get(r, 'absent')
            elif maker is not None:                     # a file of a step that has ended (a share owner's)
                up[r] = self.hasher.get(ROOT / r)[1]
            else:
                up[r] = self.hasher.get(ROOT / r)[1] if (ROOT / r).exists() else 'absent'
        return dict(sorted(up.items()))

    def key_parts(self, step):
        parts = {**self.static(), 'step': step.kind, 'build': step.build, 'args': step.args,
                 'sources': self.sources(step), 'upstream': self.upstream(step)}
        if step.kind == 'slice':
            parts['orca'] = self.orca()
        if step.quick is not None:
            parts['checks'] = step.quick
        # the stat of every file the key was made from, as hashed: a step whose inputs change while it runs (even an
        # edit undone before it ends) is not stored, since which version it read is unknown
        files = [SRC / f'{m}.py' for m in parts['sources']] + [ROOT / r for r in parts['upstream']]
        step.in_stats = {**self.hw_stats, **{str(f): self.hasher.seen(f) for f in files}}
        return parts

    # ---------------------------------------------------------------- entries
    def entry_dir(self, step):
        return CACHE / 'steps' / step.id.replace(':', '@')

    def find(self, step, key):
        f = self.entry_dir(step) / f'{key}.json'
        if self.o.no_cache or not f.exists():
            return None
        e = json.loads(f.read_text())
        blobs = [o['sha'] for o in e['outputs'].values()] + ([e['log']] if e.get('log') else [])
        return e if all(cache.blob_ok(h) for h in blobs) else None

    def why(self, step, parts):
        """--why: what changed since the step's newest run (made or used; under --quick, the full run of the same
        inputs when there is one); or, when its key is in the cache, why it runs anyway."""
        if (self.entry_dir(step) / f'{cache.digest(parts)}.json').exists():
            return ('its key is in the cache: --verify reruns it' if self.o.verify else
                    'its key is in the cache: --no-cache' if self.o.no_cache else
                    'its key is in the cache, but a file of it is missing (blobs pruned?)')
        ents = [f for f in self.entry_dir(step).glob('*.json') if f.name != 'last.json']
        if not ents:
            return 'no earlier run'
        full = self.entry_dir(step) / f"{cache.digest({k: v for k, v in parts.items() if k != 'checks'})}.json"
        if 'checks' in parts and full.exists():         # --quick: against the full run of the same inputs
            ents = [full]
        last = json.loads(max(ents, key=lambda f: f.stat().st_mtime).read_text())['parts']
        diff = []
        for k in sorted(set(parts) | set(last)):
            a, b = last.get(k), parts.get(k)
            if a == b:
                continue
            if isinstance(a, dict) and isinstance(b, dict):
                ks = sorted(x for x in set(a) | set(b) if a.get(x) != b.get(x))
                diff.append(f"{k}: {', '.join(ks[:6])}{' ...' if len(ks) > 6 else ''}")
            else:
                diff.append(k)
        return '; '.join(diff) or 'same key, entry missing (blobs pruned?)'

    def restore(self, step, e):
        """Make the disk hold the entry's files (copying only what differs) and none it deleted."""
        for r, o in e['outputs'].items():
            p = ROOT / r
            if p.exists() and self.hasher.get(p)[0] == o['sha']:
                continue
            if not cache.blob_restore(o['sha'], p):
                raise Failed(f'{step.id}: blob of {r} missing or damaged')
            self.hasher.known(p, o['sha'], o.get('masked', o['sha']))
        for r in e.get('deleted', []):
            (ROOT / r).unlink(missing_ok=True)
        self.cleanup(step, e)

    def cleanup(self, step, e):
        """Files the step owned after its last full run or restore, but not in this one: removed (what it would no
        longer make); then this entry's files become the ones it owns."""
        lf = self.entry_dir(step) / 'last.json'
        try:
            last = json.loads(lf.read_text())['outputs']
        except (OSError, ValueError, KeyError):
            last = []
        for r in last:
            if r not in e['outputs']:
                (ROOT / r).unlink(missing_ok=True)
        cache.atomic_write(lf, json.dumps({'outputs': sorted(e['outputs'])}).encode())

    def store(self, step, key, parts, written, deleted, logf, wall, memos=()):
        outs = {}
        for r in written:
            raw, m = self.hasher.get(ROOT / r)
            cache.blob_put(ROOT / r, raw)
            outs[r] = {'sha': raw, 'masked': m, 'size': (ROOT / r).stat().st_size}
        e = {'id': step.id, 'key': key, 'parts': parts, 'outputs': dict(sorted(outs.items())), 'deleted': sorted(deleted),
             'phase1': step.phase1, 'log': cache.blob_put(logf) if logf and logf.exists() else None,
             'memos': list(memos), 'wall_s': round(wall, 1), 'created': time.strftime('%Y-%m-%d %H:%M:%S'),
             **{k: step.job_stats[k] for k in ('peak_gb', 'cpu_s') if k in step.job_stats}}
        cache.atomic_write(self.entry_dir(step) / f'{key}.json', json.dumps(e, indent=1).encode())
        return e

    def touch(self, step, key):
        """Date a served entry now: its file date is when it was last made or used (prune keeps the newest; --why
        and --quick compare with the newest)."""
        try:
            os.utime(self.entry_dir(step) / f'{key}.json')
        except OSError as ex:
            log(f'{step.id}: cache entry date not refreshed ({ex})')

    # ---------------------------------------------------------------- running
    def env(self, step):
        env = {k: v for k, v in os.environ.items()
               if k not in ('SILKSCREEN_VARIANT', 'SILKSCREEN_PHASE1', 'SILKSCREEN_CHECKS', 'SILKSCREEN_SHARE_ASK')}
        env['PYTHONUNBUFFERED'] = '1'
        if self.o.no_cache and cache.MODE != 'off':
            env['SILKSCREEN_CACHE_MODE'] = 'refresh'
            env['SILKSCREEN_REFRESH_SINCE'] = repr(self.since)  # a memo is computed once in this run (cache.memo_get)
        if step.build and step.kind in SCRIPT:
            env['SILKSCREEN_VARIANT'] = step.build
        return env

    def audit_ok(self, step, audit, sources, written):
        """The reads and writes _step.py saw, against the step's key and its own files. -> problems."""
        n = os.path.normcase
        allowed = {n(str(SRC / f'{m}.py')) for m in sources} | self.hw_files
        allowed |= {n(str(ROOT / r)) for r in self.upstream(step)}
        own = {n(str(ROOT / r)) for r in written}
        cdir = (n(str(CACHE)) + os.sep, n(str(cache.MEMO)) + os.sep)      # the cache and its memos (wherever they are)
        pyc = n(str(SRC / '__pycache__')) + os.sep
        bad = []
        for p in audit['reads']:
            if p in allowed or p in own or p.startswith(cdir) or (step.in_scope(p + os.sep + 'x') and os.path.isdir(p)):
                continue
            if p.startswith(pyc) and Path(p).name.split('.')[0] in sources:
                continue
            if not os.path.exists(p):                   # a probe for a file that is not there (ezdxf.ini)
                continue
            bad.append(f'undeclared input: {p}' + (' (an old output of its own)' if step.in_scope(p) else ''))
        dirs = {n(str(SRC)), n(str(ROOT)), n(str(SRC / '__pycache__'))}
        hwd = n(str(ROOT / 'hardware'))
        for p in audit['lists']:
            if p in dirs or p == hwd or p.startswith(hwd + os.sep) or p.startswith(cdir) or p.rstrip(os.sep) + os.sep in cdir:
                continue
            if step.in_scope(p + os.sep + 'x') or step.in_scope(p) or any(o.startswith(p + os.sep) for o in own):
                continue
            bad.append(f'undeclared listing: {p}')
        for p in audit['writes']:
            if not (step.in_scope(p) or p.startswith(cdir)):
                bad.append(f'write outside its files: {p}')
        return bad

    def run_step(self, step, key, parts):
        """Run the step's process; store it when it is cached, exited 0 and its audit is clean."""
        before = step.scope()
        run = CACHE / 'run'
        run.mkdir(parents=True, exist_ok=True)
        tag = step.id.replace(':', '@')
        audit_f, marker = run / f'{tag}.audit.json', run / f'{tag}.phase1'
        ask = run / f'{tag}.share'                     # build.py's share questions: <ask>.<check>.ask / .answer
        for f in (audit_f, marker, Path(str(marker) + '.checks'),
                  *(Path(f'{ask}.{c}.{x}') for c in SHARE_REPORTS for x in ('ask', 'answer'))):
            f.unlink(missing_ok=True)
        step.shared = {}
        env = self.env(step)
        if step.kind == 'build':
            env['SILKSCREEN_PHASE1'] = str(marker)
            if step.quick is not None:
                env['SILKSCREEN_CHECKS'] = step.quick if isinstance(step.quick, str) else ','.join(step.quick)
            elif step.share_cands and not self.o.unshared:
                env['SILKSCREEN_SHARE_ASK'] = str(ask)
            logf = step.dir / 'build.log'
        else:
            logf = CACHE / 'logs' / f'{tag}.log'
        logf.parent.mkdir(parents=True, exist_ok=True)
        if step.kind in SCRIPT:
            cmd = [sys.executable, '-B', str(SRC / '_step.py'), str(audit_f), str(SRC / step.script), *step.args]
            cwd = ROOT
        elif step.kind == 'finish-only':               # build.py --finish <builds> --only, its share claims memoised
            cmd = [sys.executable, '-B', str(SRC / 'finish_step.py'), *step.args]
            cwd = ROOT
        elif step.kind.startswith('finish'):
            cmd = [sys.executable, '-B', str(SRC / 'build.py'), *step.args]
            cwd = ROOT
        elif step.kind == 'configs-slice':
            cmd = [sys.executable, '-B', str(SRC / 'configs_slice.py'), *step.args]
            cwd = ROOT
        else:                                           # plates3mf, configs
            cmd = [sys.executable, '-B', str(ENCL / 'make_plates.py'), *step.args]
            cwd = ENCL
        with open(logf, 'w') as lf:
            job = jobs.Job(cmd, cwd=cwd, env=env, stdout=lf, stderr=subprocess.STDOUT)
            self.sched.attach(step, job)
            try:
                proc = job.proc
                while proc.poll() is None:
                    if step.kind == 'build' and not step.phase1_ev.is_set() and marker.exists():
                        self.reach_phase1(step, before)
                    if 'SILKSCREEN_SHARE_ASK' in env:
                        self.answer_asks(step, ask)
                    time.sleep(0.5)
                step.job_stats = job.stats()
            finally:
                job.close()
        if step.shed:
            raise Shed(step.id)
        if proc.returncode:
            raise Failed(f'{step.id} exited {proc.returncode} (log: {logf})')
        if step.kind == 'build' and not step.phase1_ev.is_set():
            self.reach_phase1(step, before)
        if step.shared:
            self.copy_shared(step)
        after = step.scope()
        written = sorted(r for r, s in after.items() if before.get(r) != s)
        deleted = sorted(r for r in before if r not in after)
        for r in step.phase1:
            if after.get(r) != self.p1stat.get((step.id, r)):
                raise Failed(f'{step.id}: {r} changed after build_all (a check wrote a part)')
        step.outputs = {r: self.hasher.get(ROOT / r)[0] for r in sorted(after)} if step.kind in SCRIPT else {}
        if not step.cached or step.quick is not None or cache.MODE == 'off':
            return
        audit = json.loads(audit_f.read_text())
        bad = self.audit_ok(step, audit, parts['sources'], written)
        now = self.sources(step)
        if now != parts['sources']:                     # edited while it ran: which version did it run?
            bad.append('sources changed while it ran: ' + ', '.join(m for m in now if now[m] != parts['sources'].get(m)))
        moved = [f for f, s in getattr(step, 'in_stats', {}).items() if stat_sig(f) != s]
        if moved:
            bad.append('inputs changed while it ran: ' + ', '.join(Path(f).name for f in moved[:8])
                       + (' ...' if len(moved) > 8 else ''))
        if bad:
            raise Failed(f'{step.id}: not stored:\n    ' + '\n    '.join(bad[:20]))
        old = getattr(step, 'verify', None)
        if old is not None:                             # --verify: the same key must give the same files
            new = {r: self.hasher.get(ROOT / r)[1] for r in written}
            was = {r: o.get('masked', o['sha']) for r, o in old['outputs'].items()}
            diff = sorted(r for r in set(new) | set(was) if new.get(r) != was.get(r))
            with self.lock:
                self.verified.append((step.id, diff))
            log(f"{step.id}: verify: {'the same ' + str(len(new)) + ' files' if not diff else 'DIFFERS: ' + ', '.join(diff)}")
            if diff:
                raise Failed(f'{step.id}: --verify: a rerun differs from its cache entry: {diff}')
        e = self.store(step, key, parts, written, deleted, logf if step.kind == 'build' else None, time.time() - step.t0,
                       memos_of(audit))
        self.cleanup(step, e)

    # ---------------------------------------------------------------- shares (guard.py, mechanics_share.py)
    def guard_item(self, build, item):
        """The guard digest of build's item (guard.py), or None while its guard step has not passed."""
        g = self.by.get(('guard', build))
        if g is None or not g.done_ev.is_set() or not g.ok:
            return None
        with self.lock:
            if build not in self.guards:
                try:
                    self.guards[build] = json.loads((GUARDS / f'{build}.json').read_text())
                except (OSError, ValueError):
                    return None
            d = self.guards[build]
        return (d.get(item) or {}).get('digest')

    def decide_share(self, step, check):
        """The first candidate whose guard digest for the check is this build's own, or None (run it here)."""
        mine = self.guard_item(step.build, check)
        if mine is None:
            return None
        for y in step.share_cands.get(check, ()):
            if self.guard_item(y, check) == mine:
                return y
        return None

    def answer_asks(self, step, ask):
        for check in step.share_cands:
            q, a = Path(f'{ask}.{check}.ask'), Path(f'{ask}.{check}.answer')
            if q.exists() and not a.exists():
                y = self.decide_share(step, check)
                if y:
                    step.shared[check] = y
                cache.atomic_write(a, (f'share {y}' if y else 'compute').encode())
                log(f'{step.id}: {check}: ' + (f'shared from {y} (the same guard)' if y else
                                               'run here (no candidate with this guard'
                                               + (' yet' if self.guard_item(step.build, check) is None else '') + ')'))

    def copy_shared(self, step):
        """The reports this build took from others: copied once each owner's build has ended (this step gives its
        CPU and memory back while it waits), before the build is stored, so its entry holds them as always."""
        self.sched.release(step)
        for check, y in sorted(step.shared.items()):
            ys = self.by[('build', y)]
            ys.done_ev.wait()
            if not ys.ok:
                raise Failed(f'{step.id}: {check} was to come from {y}, which failed')
            src, dst = OUT / y / SHARE_REPORTS[check], step.dir / SHARE_REPORTS[check]
            cache.atomic_write(dst, src.read_bytes())
            log(f'{step.id}: {SHARE_REPORTS[check]} copied from {y}')

    def decide_mech(self, step):
        """mechanics: mechanics_share.py when a print build of its chin has the same side-key guard for every key of
        this build and (with the bottom keys) the same mech_kk guard, and its mechanics.json is made; else mechanics.py."""
        c = variants.parse(step.build)
        mine = self.guard_item(step.build, 'mech_sks')
        kk = self.guard_item(step.build, 'mech_kk') if c.bottom_keys else None
        if mine is None or (c.bottom_keys and kk is None):
            return
        ok = [b for b in step.mech_cands if self.by.get(('mechanics', b)) is not None and self.by[('mechanics', b)].ok]
        sks = next((b for b in ok if all((self.guard_item(b, 'mech_sks') or {}).get(r) == d for r, d in mine.items())), None)
        kkf = next((b for b in ok if self.guard_item(b, 'mech_kk') == kk), None) if c.bottom_keys else None
        if sks is None or (c.bottom_keys and kkf is None):
            return
        step.script = 'mechanics_share.py'
        step.args = ['--sks-from', sks] + (['--kk-from', kkf] if kkf else [])
        step.reads = [(f'out/{b}/mechanics.json', self.by[('mechanics', b)]) for b in sorted({sks, kkf} - {None})]
        step.share_note = f' (side_key_sweep from {sks}' + (f', key_hooks and key_sweep from {kkf}' if kkf else '') + ')'

    def audit_mech(self):
        """--unshared --verify, after every step: each mechanics.json that mechanics.py made in this run for a build
        whose mechanics the shares compose must be byte-identical to the one mechanics_share.py made from the same
        inputs. Compared with every entry of the step whose script is mechanics_share.py and whose key holds what a
        shared run would hold now: the same static parts (environment, hardware, path), the same build parts
        (upstream), the code as it is now (closure(mechanics_share)), and owners' mechanics.json files equal to the
        ones on disk (the owners' own steps check those). A difference fails the run; a build with no such entry is
        named as not audited (run it shared first)."""
        want = {m: self.hasher.get(SRC / f'{m}.py')[0] for m in cache.closure('mechanics_share') if m not in NOT_CODE}
        done, none = 0, []
        for s in self.steps:
            if s.kind != 'mechanics' or s.status != 'ran' or s.build in MECH_OWNERS or s.parts is None:
                continue
            r = f'out/{s.build}/mechanics.json'
            new = self.hasher.get(ROOT / r)[0]
            seen = 0
            for f in sorted(self.entry_dir(s).glob('*.json')):
                if f.name == 'last.json':
                    continue
                try:
                    e = json.loads(f.read_text())
                except (OSError, ValueError):
                    continue
                ep = e.get('parts') or {}
                if ep.get('sources') != want or r not in e.get('outputs', {}):
                    continue
                if any(ep.get(k) != s.parts.get(k) for k in ('format', 'root', 'env', 'hardware', 'step', 'build')):
                    continue
                up = ep.get('upstream') or {}
                if any(up.get(k) != v for k, v in s.parts['upstream'].items()):
                    continue
                own = {k: v for k, v in up.items() if k not in s.parts['upstream']}
                if not all(k.endswith('/mechanics.json') and (ROOT / k).exists() and self.hasher.get(ROOT / k)[1] == v
                           for k, v in own.items()):
                    continue
                seen += 1
                same = e['outputs'][r]['sha'] == new
                log(f"{s.id}: audit: mechanics.json {'equals' if same else 'DIFFERS FROM'} mechanics_share.py's "
                    f"({' '.join(ep.get('args') or [])}; entry {f.stem[:12]}, {e.get('created')})")
                if not same:
                    with self.lock:
                        self.failed.append(f'{s.id}: --unshared --verify: mechanics.py gives another mechanics.json '
                                           f'than mechanics_share.py ({" ".join(ep.get("args") or [])}, entry '
                                           f'{f.stem[:12]})')
            if seen:
                done += 1
            else:
                none.append(s.build)
        if done or none:
            log(f'mechanics share audit: {done} build(s) compared'
                + (f"; not audited (no entry of mechanics_share.py for these inputs): {', '.join(none)}" if none else ''))

    def reach_phase1(self, step, before):
        now = step.scope()
        p1 = sorted(r for r, s in now.items() if before.get(r) != s)
        with self.lock:
            for r in p1:
                self.p1stat[(step.id, r)] = now[r]
        step.phase1 = {r: self.hasher.get(ROOT / r)[1] for r in p1}
        step.phase1_s = time.time() - step.t0
        if step.quick == 'auto':
            checks = self.quick_checks(step)
            Path(str(CACHE / 'run' / f"{step.id.replace(':', '@')}.phase1") + '.checks').write_text(','.join(checks))
            log(f'{step.id}: quick checks: {", ".join(checks) or "none"}')
        log(f'{step.id}: parts written ({len(p1)} files, {time.time() - step.t0:.0f}s)')
        step.phase1_ev.set()

    def quick_checks(self, step):
        """--quick: the checks that read a part that differs from the last full run's (CHECK_PARTS), or every check
        when there is no full run of this build in the cache, or the checks' code or the hardware changed since."""
        cur, hwk = self.sources(step), self.static()['hardware']
        refs = []                                       # full runs with the same checks' code and hardware
        for f in self.entry_dir(step).glob('*.json'):
            if f.name != 'last.json':
                e = json.loads(f.read_text())
                if e['parts']['hardware'] == hwk and all(cur.get(m) == e['parts']['sources'].get(m) for m in CHECK_CODE):
                    refs.append((f.stat().st_mtime, e))
        if not refs:
            return list(CHECKS)
        ref = max(refs, key=lambda x: x[0])[1]
        old = ref['phase1']
        changed = {Path(r).stem for r in set(old) | set(step.phase1) if old.get(r) != step.phase1.get(r)}
        return [c for c in CHECKS if any(fnmatch.fnmatch(n, pat) for n in changed for pat in CHECK_PARTS[c])]

    def worker(self, step):
        try:
            for d, what in step.deps:
                (d.phase1_ev if what == 'phase1' else d.done_ev).wait()
                if d.ok is False and d not in step.soft:
                    raise Failed(f'{step.id}: skipped ({d.id} failed)')
            # also in a --dry-run (its guards and owners were restored as in a real run; when one of them would run,
            # so does this step, just below), so it names the entry a real run would find, not mechanics.py's
            if step.mech_cands and not self.o.unshared:
                self.decide_mech(step)
            if self.o.dry_run and any(d.status == 'would run' for d, _ in step.deps):
                step.status, step.ok = 'would run', True
                log(f'{step.id}: would run (after the steps before it)')
                return
            step.t0 = time.time()
            if step.cached:
                parts = step.parts = self.key_parts(step)
                key = cache.digest(parts)
                e = self.find(step, key) if step.quick is None else None
                gone = date_memos(e.get('memos', ())) if e is not None else []
                if gone:
                    log(f'{step.id}: {len(gone)} memo file(s) its cached run read are gone (a `cache.py prune`?): a '
                        f'rerun (--verify) computes them again, and an OrcaSlicer G-code then differs. Before a '
                        f'--verify, run --builds {step.build} --no-cache (a new entry and new memos)')
                if e is not None and self.o.verify:
                    step.verify = e
                    e = None
                if e is not None:
                    self.restore(step, e)
                    self.touch(step, key)
                    if step.kind == 'build':
                        step.phase1 = e['phase1']
                        log_b = cache.blob_path(e['log']).read_bytes() if e.get('log') else b''
                        note = log_b + (f"\n[pipeline] restored from the cache (key {key[:12]}, run {e['created']}, "
                                        f"{e['wall_s']} s)\n").encode()
                        lp = step.dir / 'build.log'
                        try:                            # in place, as build.py always wrote it (it may be tailed);
                            # left alone when it already is this entry's log (the run's own, or as restored), so a warm
                            # or --dry-run run does not touch out/<build>/ (the showcase's check_fresh reads its mtimes)
                            if not lp.exists() or lp.read_bytes() not in (log_b, note):
                                lp.write_bytes(note)
                        except OSError as ex:
                            log(f'{step.id}: build.log not rewritten ({ex})')
                        step.phase1_ev.set()
                        self.unmark_quick(step)
                    step.outputs = {r: o['sha'] for r, o in e['outputs'].items()}
                    step.status = 'hit'
                    step.ok = True
                    step.t1 = time.time()
                    log(f'{step.id}: cached ({e["wall_s"]:.0f} s saved)')
                    return
                why = f' ({self.why(step, parts)})' if self.o.why else ''
                if self.o.dry_run:
                    step.status, step.ok = 'would run', True
                    log(f'{step.id}: would run{why}')
                    step.phase1_ev.set()
                    return
            else:
                key = parts = None
                why = ''
                if self.o.dry_run:
                    step.status, step.ok = 'would run', True
                    step.phase1_ev.set()
                    return
            while True:                                 # 'running' only once the scheduler admits it
                self.sched.acquire(step)
                try:
                    log(f'{step.id}: running ({step.admit_note}){step.share_note}{why}')
                    step.t0 = time.time()
                    self.run_step(step, key, parts)
                except Shed:
                    log(f'{step.id}: queued again after the safety valve ended it')
                    step.shed = False
                    continue
                finally:
                    self.sched.release(step)
                break
            self.note_stats(step, time.time() - step.t0)
            if step.kind == 'build':
                if step.quick is not None:
                    self.mark_quick(step)
                else:
                    self.unmark_quick(step)
            step.status, step.ok, step.t1 = 'ran', True, time.time()
            log(f'{step.id}: done ({step.t1 - step.t0:.0f} s)')
        except Exception as ex:
            step.ok, step.status, step.t1 = False, 'failed', time.time()
            with self.lock:
                self.failed.append(f'{step.id}: {ex}')
            log(f'{step.id}: FAILED: {ex}')
        finally:
            step.phase1_ev.set()
            step.done_ev.set()

    def mark_quick(self, step, on=True):
        f = CACHE / 'quick.json'
        with self.lock:
            try:
                q = json.loads(f.read_text())
            except (OSError, ValueError):
                q = {}
            if on:
                q[step.build] = {'checks': step.quick, 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
            else:
                q.pop(step.build, None)
            cache.atomic_write(f, json.dumps(q, indent=1).encode())

    def unmark_quick(self, step):
        self.mark_quick(step, on=False)

    def go(self):
        self.p1stat = {}
        t0 = time.time()
        self.prepare()
        self.sched = Scheduler(self.o.cpu, self.o.mem_floor, self)
        threads = [threading.Thread(target=self.worker, args=(s,), daemon=True) for s in self.steps]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if self.o.unshared and self.o.verify and not self.o.dry_run:
                self.audit_mech()
        finally:
            self.sched.stop.set()
            self.hasher.save()
            if not self.o.dry_run:
                with self.lock:
                    cache.atomic_write(STATS, json.dumps(self.stats, indent=1).encode())
        wall = time.time() - t0
        rows = [{'step': s.id, 'status': s.status, 'start_s': round(s.t0 - t0, 1) if s.t0 else None,
                 'wall_s': round(s.t1 - s.t0, 1) if s.t0 and s.t1 else None,
                 **{k: s.job_stats[k] for k in ('peak_gb', 'cpu_s') if k in s.job_stats}} for s in self.steps]
        cache.atomic_write(CACHE / 'runs' / f"{time.strftime('%Y%m%d-%H%M%S')}.json",
                           json.dumps({'argv': sys.argv, 'wall_s': round(wall, 1), 'steps': rows}, indent=1).encode())
        n = {k: sum(1 for s in self.steps if s.status == k) for k in ('hit', 'ran', 'failed', 'would run', 'waiting')}
        log(f"pipeline: {wall:.0f} s; {n['hit']} cached, {n['ran']} ran"
            + (f", {n['would run']} would run" if n['would run'] else '') + (f", {n['failed']} failed" if n['failed'] else ''))
        try:
            q = json.loads((CACHE / 'quick.json').read_text())
        except (OSError, ValueError):
            q = {}
        if q:
            log(f"quick builds (their check reports are from --quick; a full run replaces them): {', '.join(q)}")
        if self.failed:
            raise SystemExit('pipeline failed:\n  ' + '\n  '.join(self.failed))


def parse(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pipeline.py', description=__doc__.split('\n')[0])
    ap.add_argument('--builds', default='all', help='slugs and presets (' + ', '.join(PRESETS) + '), comma-separated')
    ap.add_argument('--steps', default=','.join(KINDS), help='of ' + ','.join(KINDS))
    ap.add_argument('--finish', choices=('auto', 'default', 'only', 'none'), default='auto')
    ap.add_argument('--plates3mf', choices=('auto', 'yes', 'no'), default='auto')
    ap.add_argument('--configs', choices=('auto', 'yes', 'no'), default='auto',
                    help='the per-configuration projects of the builds asked for (auto: when their plates are made)')
    ap.add_argument('--cpu', '--jobs', dest='cpu', type=float, default=None,
                    help='CPU cap: the CPU weights of the steps running at once (default: the physical cores; --jobs '
                    'is the old name)')
    ap.add_argument('--mem-floor', type=float, default=8.0,
                    help='GB of commit charge the scheduler keeps free (default 8)')
    ap.add_argument('--blas', choices=('one', 'default'), default='one',
                    help="one: OPENBLAS_NUM_THREADS=1 for every step (a quarter of the memory; in every step's key); "
                    "default: OpenBLAS as installed (a thread per logical processor)")
    ap.add_argument('--unshared', action='store_true',
                    help='no shares: every build runs every check and mechanics.py (the audit; with --verify each '
                    "build's rerun is compared with its cache entry, the shared reports in it, and each mechanics.json "
                    'with the entries mechanics_share.py made from the same inputs)')
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--rehash', action='store_true')
    ap.add_argument('--why', action='store_true')
    ap.add_argument('--verify', action='store_true', help='rerun the cached steps and check they give their files again')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--checks', default=None, help='--quick: the checks to run (CHECKS, or none), default: by changed parts')
    ap.add_argument('--prune', type=int, default=3, help='after a run that passed: keep the N most recently used cache '
                    'entries of each step and the blobs and memo files they name, and the other memos used in the '
                    'last cache.MEMO_DAYS days (0: never prune)')
    ap.add_argument('rest', nargs='*', help='after --: arguments for the build children')
    return ap.parse_args(argv)


def plan(o):
    builds = expand(o.builds)                           # what was asked for, every step kind of each
    run = with_twins(builds)                            # + the twins their checks compare with: builds only
    kinds = [k for k in o.steps.split(',') if k]
    assert set(kinds) <= set(KINDS), f'--steps: {kinds} (of {KINDS})'
    if o.quick and o.steps == ','.join(KINDS):
        kinds = ['build']
    P = Pipeline(o)
    P.builds, P.pulled = builds, [b for b in run if b not in builds]
    by = {}
    for b in run:
        for k in KINDS:
            s = Step(k, b, args=[*o.rest, '--no-share'] if k == 'build' else [],
                     prio=PRIORITY[b] + PRIORITY_STRIDE * KINDS.index(k), cached=True)
            by[(k, b)] = s
    for b in run:
        bs = by[('build', b)]
        for t, files in cross_reads(b):                 # with_twins put every one of them in the run
            maker = by[('build', t)]
            bs.reads += [(f'out/{t}/{f}', maker) for f in files]
            bs.deps.append((maker, 'phase1'))
        if o.quick:
            bs.quick = 'auto' if o.checks is None else [c for c in o.checks.split(',') if c and c != 'none']
        by[('mechanics', b)].deps = [(bs, 'phase1')]
        by[('dummy', b)].deps = [(bs, 'phase1')]
        by[('plates', b)].deps = [(bs, 'phase1'), (by[('dummy', b)], 'done')]
        by[('slice', b)].deps = [(bs, 'phase1'), (by[('plates', b)], 'done')]
    need = {('build', b) for b in run}
    for b in builds:                                    # a step brings the steps whose files it reads
        for k in kinds:
            need.add((k, b))
            if k in ('plates', 'slice'):
                need.add(('dummy', b))
            if k == 'slice':
                need.add(('plates', b))
    P.steps = [by[x] for x in sorted(need, key=lambda x: (KINDS.index(x[0]), PRIORITY[x[1]]))]
    P.by = by
    if not o.unshared and not o.quick:                  # the shares (SHARE_REPORTS, MECH_OWNERS, guard.py)
        guarded = set()
        for b in run:
            c = variants.parse(b)
            for check, has in SHARE_HAS.items():
                cands = sorted((a for a in ancestors(b) if a in run and has(variants.parse(a))), key=PRIORITY.get)
                if has(c) and cands:
                    by[('build', b)].share_cands[check] = cands
                    guarded |= {b, *cands}
        for b in builds:
            c = variants.parse(b)
            cands = [m for m in MECH_OWNERS if ('mechanics', m) in need and m != b
                     and variants.parse(m).bottom_keys == c.bottom_keys]
            if ('mechanics', b) in need and b not in MECH_OWNERS and cands:
                by[('mechanics', b)].mech_cands = cands
                guarded |= {b, *cands}
        for b in sorted(guarded, key=PRIORITY.get):
            g = by[('guard', b)] = Step('guard', b, prio=PRIORITY[b])
            g.deps = [(by[('build', b)], 'phase1')]
            P.steps.append(g)
        for b in builds:
            ms = by[('mechanics', b)]
            if ms.mech_cands:
                extra = [(by[('guard', x)], 'done') for x in (b, *ms.mech_cands)]
                extra += [(by[('mechanics', m)], 'done') for m in ms.mech_cands]
                ms.deps += extra
                ms.soft |= {d for d, _ in extra}

    def done(bs_):
        """The build steps the share checks of bs_ read: their own and every twin's (build.twin_shares)."""
        return [(by[('build', x)], 'done') for x in sorted({*bs_, *(t for b in bs_ for _, t in variants.twins(b))},
                                                           key=PRIORITY.get)]
    fin = o.finish
    if fin == 'auto':
        fin = 'none' if o.quick or 'build' not in kinds else 'both'
    pb = [b for b in PRINT_BUILDS if b in builds]
    fd = None
    if fin in ('default', 'both') and len(pb) == len(PRINT_BUILDS):
        fd = Step('finish-default', args=['--finish', ','.join(PRINT_BUILDS)], cached=False)
        fd.deps = done(PRINT_BUILDS)
        P.steps.append(fd)
    elif fin == 'default':
        raise SystemExit(f'--finish default needs every print build ({", ".join(PRINT_BUILDS)})')
    elif fin == 'both':
        log('print/4.26/ and the plate files are not made in this run: it lacks the print build(s) '
            + ', '.join(b for b in PRINT_BUILDS if b not in builds) + ' (--builds print, six or all has them)'
            + (f"; the share checks of {', '.join(pb)} run in finish-only" if pb else ''))
    # finish-only: every asked build whose share checks finish-default does not run (all of them without it)
    ob = [b for b in builds if b not in PRINT_BUILDS or fd is None]
    if (fin == 'both' and ob) or fin == 'only':
        f = Step('finish-only', args=[','.join(ob)], cached=False)       # finish_step.py: build.py --finish .. --only
        # after finish-default when both run: each writes its builds into out/shares-all.json (build.twin_shares)
        f.deps = done(builds) + ([(fd, 'done')] if fd else [])
        P.steps.append(f)
    p3 = o.plates3mf == 'yes' or (o.plates3mf == 'auto' and not o.quick and 'plates' in kinds
                                  and len(pb) == len(PRINT_BUILDS) and fin in ('default', 'both'))
    if p3:
        f = Step('plates3mf', cached=False)
        f.deps = [(by[('plates', b)], 'done') for b in PRINT_BUILDS] + [(s, 'done') for s in P.steps if s.kind == 'finish-default']
        P.steps.append(f)
    # the per-configuration projects (make_plates.py configs), from the asked-for builds' print STLs and lids, once
    # their builds (every check), plates and the share checks have passed; then their read-back slices
    pc = o.configs == 'yes' or (o.configs == 'auto' and not o.quick and 'plates' in kinds)
    if pc:
        f = Step('configs', args=['configs', '--builds', ','.join(builds)], cached=False)
        f.deps = [(s, 'done') for s in P.steps if (s.build in builds and s.kind in ('build', 'plates'))
                  or s.kind.startswith('finish')]
        P.steps.append(f)
        if 'slice' in kinds:
            # (it waits on every slice step anyway; prio only breaks ties: order_key puts the b-level first)
            g = Step('configs-slice', args=['--builds', ','.join(builds)], cached=False, prio=10 ** 6)
            g.deps = [(f, 'done')] + [(s, 'done') for s in P.steps if s.kind == 'slice']   # Orca's slots are theirs
            P.steps.append(g)
    return P


def path_guard(P):
    """OrcaSlicer fails (exit -100, "GCode processor post process export failed. Cannot open file for writing.") on a
    G-code path of cache.ORCA_PATH_MAX characters or more, and its failure reads like a slicing error: so the longest
    path a slice step of this run would write (out/<build>/slice/coupon-chin/plate_1.gcode, for its longest build
    name) is checked before anything runs."""
    sliced = [OUT / s.build / SLICE_LONGEST for s in P.steps if s.kind == 'slice']
    sliced += [CONFIGS_SLICE / b / 'plate_2.gcode' for s in P.steps if s.kind == 'configs-slice' for b in P.builds]
    if not sliced:
        return
    worst = max(sliced, key=lambda p: len(str(p)))
    if len(str(worst)) >= cache.ORCA_PATH_MAX:
        raise SystemExit(f'path too long for OrcaSlicer: {worst} is {len(str(worst))} characters, and it fails at '
                         f'{cache.ORCA_PATH_MAX} or more. Run from a checkout whose path is at least '
                         f'{len(str(worst)) - cache.ORCA_PATH_MAX + 1} characters shorter (or without the slice step).')


def prime():
    """The board's solids cache (hardware/cache), rebuilt by hw.py when board.step is newer: once, before any step
    (as build.py always did), so no step rebuilds it and every key sees it as it will be."""
    idx, step = ROOT / 'hardware' / 'cache' / 'index.json', ROOT / 'hardware' / 'board.step'
    if not idx.exists() or idx.stat().st_mtime < step.stat().st_mtime:
        log('hardware cache: rebuilding from board.step')
        subprocess.run([sys.executable, '-B', '-c', 'import hw; hw.solids()'], cwd=SRC, check=True)


def main(argv=None):
    o = parse(sys.argv[1:] if argv is None else argv)
    if cache.MODE in ('refresh', 'off'):                # SILKSCREEN_CACHE_MODE: no step is served from the cache
        o.no_cache = True
    if o.cpu is None:
        o.cpu = float(jobs.physical_cores())
    # before any key: cache.env_fingerprint() reads the *_NUM_THREADS settings from this process's environment, and
    # every step's environment is a copy of it, so the keys follow the setting (a caller's own value is kept)
    if o.blas == 'one':
        os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    lock = cache.Lock(CACHE / 'run' / 'pipeline.lock')
    if not lock.acquire(block=False):
        raise SystemExit(f'another pipeline.py runs in this checkout ({lock.path})')
    try:
        P = plan(o)
        path_guard(P)
        prime()
        log(f"pipeline: {len(P.builds)} builds" + (f" (+ their twins, as builds only: {', '.join(P.pulled)})" if P.pulled else '')
            + f", {len(P.steps)} steps ({', '.join(s.id for s in P.steps)}), --cpu {o.cpu:g}, "
            f"--mem-floor {o.mem_floor:g} GB, OPENBLAS_NUM_THREADS={os.environ.get('OPENBLAS_NUM_THREADS', '(unset)')}"
            + (' (--no-cache)' if o.no_cache else '') + (' (--quick)' if o.quick else ''))
        P.go()
        if o.prune > 0 and not o.dry_run and cache.MODE != 'off':   # P.go() raised if a step failed
            keep_memos(o.prune)
            cache.prune(o.prune)
    finally:
        lock.release()


if __name__ == '__main__':
    main()
