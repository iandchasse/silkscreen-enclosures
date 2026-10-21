"""Unit test of the pipeline's scheduler, job objects and shares (2026-10-08). No CAD is built; the real cache is
only read (plan reads stats.json), never written: what a test writes goes to a temporary folder.

    python -B src/test_pipeline.py          (from enclosures/case-426; about 30 s)

Fake steps under a patched free commit charge: the CPU cap, the memory floor (with what the running steps may still
take, read fresh at admission; also for a step that would run alone), b-level order, backfill of short steps only,
the safety valve (it ends only our own youngest sheddable step that still holds memory, and opens under the floor
itself); the estimates (per script for mechanics; an uncached step never under PEAK_GB); stats.json written as each
step passes; real processes in job objects: the peak commit and CPU time of a step whose interpreter is a child of
the venv's launcher, and KILL_ON_JOB_CLOSE (a pipeline that dies takes its steps with it). The shares: a build's
candidates (plan), deps.params_read, and the --unshared --verify audit of the composed mechanics.json (audit_mech).
"""
import subprocess, sys, threading, time
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import jobs
import pipeline as PL


class FakeStep:
    def __init__(self, sid, kind='build', est=1.0, wall=600.0, blevel=0.0, prio=0):
        self.id, self.kind, self.est, self.wall, self.blevel, self.prio = sid, kind, est, wall, blevel, prio
        self.admitted, self.admit_note, self.shed, self.shed_peak = False, '', False, 0.0
        self.phase1_ev = threading.Event()


class FakeP:
    def est_peak(self, s):
        return s.est

    def est_wall(self, s):
        return s.wall

    def order_key(self, s):
        return (-s.blevel, s.prio)

    def sheddable(self, s):
        return s.kind in PL.SHEDDABLE


class FakeJob:
    def __init__(self, gb):
        self.gb, self.ended = gb, False

    def commit(self):
        return self.gb * 1e9

    def terminate(self):
        self.ended = True


def run(steps, cpu, floor, free_gb, hold=0.3, attach=None):
    """Start a thread per step that acquires, holds `hold` s, releases; -> (admission order, max concurrent
    (count, cpu weight))."""
    PL.free_commit = lambda: free_gb() * 1e9
    S = PL.Scheduler(cpu, floor, FakeP())
    S.POLL_S = 0.05
    order, conc, lock = [], [0, 0.0], threading.Lock()

    def w(s):
        S.acquire(s)
        with lock:
            order.append(s.id)
            conc[0] = max(conc[0], len(S.running))
            conc[1] = max(conc[1], S.cpu_used())
        if attach:
            S.attach(s, attach(s))
        time.sleep(hold)
        S.release(s)
    ts = []
    for s in steps:
        t = threading.Thread(target=w, args=(s,))
        t.start()
        ts.append(t)
        time.sleep(0.01)
    for t in ts:
        t.join()
    S.stop.set()
    return order, conc, S


def test_cpu_cap():
    steps = [FakeStep(f'b{i}', est=0.1) for i in range(10)]
    _, conc, _ = run(steps, cpu=4, floor=8, free_gb=lambda: 100.0)
    assert conc[0] == 4, conc
    steps = [FakeStep(f's{i}', kind='slice', est=0.1) for i in range(10)]    # weight 0.5
    _, conc, _ = run(steps, cpu=4, floor=8, free_gb=lambda: 100.0)
    assert conc[0] == 8 and conc[1] == 4.0, conc


def test_memory_floor():
    # 12 GB free, floor 8 + 0.5 margin, 1 GB each: the 1st (11 >= 8.5), 2nd (10), 3rd (9) fit; the 4th (8) does not
    steps = [FakeStep(f'b{i}', est=1.0) for i in range(6)]
    _, conc, _ = run(steps, cpu=12, floor=8, free_gb=lambda: 12.0)
    assert conc[0] == 3, conc
    # 8.6 GB free: one runs (none of ours runs: 8.6 - 0.5 = 8.1 >= the floor), never a second
    steps = [FakeStep(f'b{i}', est=0.5) for i in range(3)]
    _, conc, _ = run(steps, cpu=12, floor=8, free_gb=lambda: 8.6)
    assert conc[0] == 1, conc


def test_alone_keeps_the_floor():
    # none of ours runs: a step starts only if free - est stays >= the floor (2026-10-10). Before, free - est >= 2 GB
    # let it start under the floor, the valve ended it, and it was admitted again at once, every 30 s
    free = [8.4]
    PL.free_commit = lambda: free[0] * 1e9
    S = PL.Scheduler(12, 8, FakeP())
    S.POLL_S = 0.05
    s = FakeStep('mech', kind='mechanics', est=0.6)
    t = threading.Thread(target=S.acquire, args=(s,))
    t.start()
    time.sleep(0.4)
    assert not s.admitted                               # 8.4 - 0.6 = 7.8 < 8: it waits
    free[0] = 7.0
    time.sleep(0.2)
    assert not s.admitted
    free[0] = 8.7                                       # 8.7 - 0.6 = 8.1 >= 8 (no margin when alone)
    t.join(2)
    assert s.admitted
    S.stop.set()


def test_stats_written_at_once():
    # a passed step's stats reach stats.json when it ends (a killed pipeline kept none); a --quick build records none
    import json, tempfile
    old = PL.STATS
    tmp = tempfile.TemporaryDirectory()
    PL.STATS = Path(tmp.name) / 'stats.json'
    try:
        P = PL.Pipeline(PL.parse([]))
        s = PL.Step('dummy', 'standard')
        s.job_stats = {'peak_gb': 0.5, 'cpu_s': 3.0}
        P.note_stats(s, 4.0)
        got = json.loads(PL.STATS.read_text())
        assert got['dummy:standard'][-1]['peak_gb'] == 0.5, got
        q = PL.Step('build', 'standard')
        q.quick, q.job_stats = 'auto', {'peak_gb': 0.1}
        P.note_stats(q, 1.0)
        assert 'build:standard' not in json.loads(PL.STATS.read_text()) and 'build:standard' not in P.stats
        assert got['dummy:standard'][-1]['script'] == 'dummy.py', got
    finally:
        PL.STATS = old
        tmp.cleanup()


def test_estimates_by_script():
    # mechanics: a composed run (mechanics_share.py) does not lower mechanics.py's estimate, nor the other way; an
    # uncached step's warm runs (memos hit) never take it under PEAK_GB
    P = PL.Pipeline(PL.parse([]))
    P.stats = {'mechanics:standard-nodev': [{'peak_gb': 0.86, 'blas': P.blas, 'script': 'mechanics.py'},
                                            {'peak_gb': 0.30, 'blas': P.blas, 'script': 'mechanics_share.py'},
                                            {'peak_gb': 0.31, 'blas': P.blas, 'script': 'mechanics_share.py'},
                                            {'peak_gb': 0.30, 'blas': P.blas, 'script': 'mechanics_share.py'}],
               'configs-slice': [{'peak_gb': 0.07, 'blas': P.blas, 'script': 'configs-slice'}] * 3}
    m = PL.Step('mechanics', 'standard-nodev')
    assert abs(P.est_peak(m) - (1.1 * 0.86 + 0.1)) < 1e-9, P.est_peak(m)
    m.script = 'mechanics_share.py'
    assert abs(P.est_peak(m) - (1.1 * 0.31 + 0.1)) < 1e-9, P.est_peak(m)
    c = PL.Step('configs-slice', cached=False)
    assert P.est_peak(c) == PL.PEAK_GB[P.blas]['configs-slice'], P.est_peak(c)


def test_owed_read_fresh():
    # admission reads what the running steps hold now (at most FRESH_S old), not the monitor's last reading: a step
    # that let memory go owes it again
    PL.free_commit = lambda: 10.5e9
    S = PL.Scheduler(12, 8, FakeP())
    S.POLL_S = 0.05
    a, b = FakeStep('a', est=2.0), FakeStep('b', est=1.0)
    S.acquire(a)
    j = FakeJob(0.5)
    S.attach(a, j)
    S.running[a]['cur'] = 2.0                           # a stale reading: it held 2 GB, now 0.5
    S.sampled = 0.0
    t = threading.Thread(target=S.acquire, args=(b,))
    t.start()
    time.sleep(0.4)
    assert not b.admitted                               # 10.5 - (2 - 0.5) - 1 = 8.0 < 8.5
    j.gb = 2.0
    t.join(3)
    assert b.admitted                                   # 10.5 - 0 - 1 = 9.5
    S.stop.set()


def test_owed_counts_what_is_held():
    # a running step that already holds its estimate owes nothing more: the next one is judged on free commit alone
    PL.free_commit = lambda: 12.0e9
    S = PL.Scheduler(12, 8, FakeP())
    a, b = FakeStep('a', est=2.0), FakeStep('b', est=2.0)
    S.acquire(a)
    assert S.owed() == 2.0
    S.attach(a, FakeJob(2.0))
    S.running[a]['cur'] = 2.0
    assert S.owed() == 0.0
    S.acquire(b)                                        # 12 - 0 - 2 = 10 >= 8.5
    assert b.admitted
    S.stop.set()


def test_blevel_order():
    # one slot: after the first, the rest start longest chain first, whatever order they asked in
    steps = [FakeStep('first', blevel=1, est=0.1)] + [FakeStep(f'b{i}', blevel=i, est=0.1) for i in (3, 9, 5, 7)]
    order, _, _ = run(steps, cpu=1, floor=8, free_gb=lambda: 100.0, hold=0.2)
    assert order == ['first', 'b9', 'b7', 'b5', 'b3'], order


def test_backfill_short_only():
    # the head (3 GB) does not fit beside the running one; a short step (1 GB, 30 s) behind it does, a long one not
    PL.free_commit = lambda: 12.0e9
    S = PL.Scheduler(12, 8, FakeP())
    S.POLL_S = 0.05
    run1 = FakeStep('run1', est=2.0, blevel=100)
    S.acquire(run1)                                     # owed 2: free for the next = 12 - 2 - est
    head = FakeStep('head', est=3.0, blevel=50)         # 12 - 2 - 3 = 7 < 8.5
    long_ = FakeStep('long', est=1.0, wall=900, blevel=40)
    short = FakeStep('short', kind='dummy', est=1.0, wall=30, blevel=30)
    got = []
    ts = [threading.Thread(target=lambda s=s: (S.acquire(s), got.append(s.id))) for s in (head, long_, short)]
    for t in ts:
        t.start()
        time.sleep(0.05)
    time.sleep(0.5)
    assert got == ['short'], got                         # 12 - 2 - 1 = 9 >= 8.5, and short
    S.release(run1)
    S.release(short)                                    # now the head fits (none of ours runs)
    time.sleep(0.5)
    assert got == ['short', 'head'], got                 # the long one: 12 - 3 (owed by head) - 1 = 8 < 8.5
    S.release(head)
    for t in ts:
        t.join(2)
    assert got == ['short', 'head', 'long'], got
    S.stop.set()


def test_safety_valve():
    # free commit falls to 5 GB: after VALVE_S the youngest sheddable step's job is ended, never a build past phase 1
    free = [20.0]
    PL.free_commit = lambda: free[0] * 1e9
    S = PL.Scheduler(12, 8, FakeP())
    S.POLL_S, S.VALVE_S = 0.05, 0.3
    b = FakeStep('build', kind='build', est=1.0)
    b.phase1_ev.set()
    m1, m2 = FakeStep('mech1', kind='mechanics', est=1.0), FakeStep('mech2', kind='mechanics', est=1.0)
    jb = {}
    for s in (b, m1, m2):
        S.acquire(s)
        jb[s.id] = FakeJob(1.0)
        S.attach(s, jb[s.id])
        time.sleep(0.05)
    free[0] = 5.0
    t0 = time.time()
    while not jb['mech2'].ended and time.time() - t0 < 6:     # (the monitor's first wait is the class's 2 s)
        time.sleep(0.1)
    time.sleep(0.5)
    assert jb['mech2'].ended and not jb['mech1'].ended and not jb['build'].ended, {k: j.ended for k, j in jb.items()}
    assert m2.shed and not m1.shed
    S.stop.set()


def test_valve_skips_a_step_that_holds_nothing():
    # the youngest sheddable step whose process has ended (its files being stored) frees nothing: the valve ends the
    # next youngest that holds memory
    free = [20.0]
    PL.free_commit = lambda: free[0] * 1e9
    S = PL.Scheduler(12, 8, FakeP())
    S.POLL_S, S.VALVE_S = 0.05, 0.3
    m1, m2 = FakeStep('mech1', kind='mechanics', est=1.0), FakeStep('mech2', kind='mechanics', est=1.0)
    jb = {}
    for s, gb in ((m1, 1.0), (m2, 0.0)):
        S.acquire(s)
        jb[s.id] = FakeJob(gb)
        S.attach(s, jb[s.id])
        time.sleep(0.05)
    free[0] = 5.0
    t0 = time.time()
    while not jb['mech1'].ended and time.time() - t0 < 6:
        time.sleep(0.1)
    assert jb['mech1'].ended and not jb['mech2'].ended, {k: j.ended for k, j in jb.items()}
    S.stop.set()


def test_valve_at_the_floor():
    # the valve opens under the floor itself (2026-10-10): 8.3 GB free with a floor of 8 sheds nothing, 7.6 GB does
    free = [20.0]
    PL.free_commit = lambda: free[0] * 1e9
    S = PL.Scheduler(12, 8, FakeP())
    S.POLL_S, S.VALVE_S = 0.05, 0.3
    assert S.valve_gb == 8
    m1, m2 = FakeStep('mech1', kind='mechanics', est=1.0), FakeStep('mech2', kind='mechanics', est=1.0)
    jb = {}
    for s in (m1, m2):
        S.acquire(s)
        jb[s.id] = FakeJob(1.0)
        S.attach(s, jb[s.id])
        time.sleep(0.05)
    free[0] = 8.3
    time.sleep(2.5)                                     # the monitor's first wait is the class's 2 s, then 0.05 s
    assert not any(j.ended for j in jb.values()), {k: j.ended for k, j in jb.items()}
    free[0] = 7.6
    t0 = time.time()
    while not jb['mech2'].ended and time.time() - t0 < 6:
        time.sleep(0.1)
    assert jb['mech2'].ended and not jb['mech1'].ended, {k: j.ended for k, j in jb.items()}
    S.stop.set()


def test_job_measures_the_interpreter():
    j = jobs.Job([sys.executable, '-B', '-c', 'import time; b = bytearray(400 * 1024 * 1024); time.sleep(2)'],
                 stdout=subprocess.DEVNULL)
    time.sleep(1.2)
    now = j.commit() / 1e9
    j.proc.wait()
    st = j.stats()
    j.close()
    if jobs.WINDOWS:
        assert 0.40 <= now <= 0.6, now                   # the launcher alone would be ~0.001
        assert 0.40 <= st['peak_gb'] <= 0.6 and st['procs'] >= 1, st


def test_kill_on_close():
    """A parent that dies (here: exits without waiting) takes the step it started in a job with it."""
    if not jobs.WINDOWS:
        return
    code = ('import sys, time, subprocess; sys.path.insert(0, %r); import jobs\n'
            'j = jobs.Job([sys.executable, "-B", "-c", "import time; time.sleep(60)"])\n'
            'print(j.pids()[-1], flush=True); time.sleep(1)\n' % str(SRC))
    p = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, timeout=60)
    pid = int(p.stdout.split()[-1])
    time.sleep(1.0)
    import cache
    assert not cache._pid_alive(pid), f'step {pid} outlived its pipeline'


def test_ancestors_and_candidates():
    """A build's share candidates are its ancestors in the run that have the check; mechanics' are the print builds
    of its chin; the print builds compute everything themselves."""
    assert PL.ancestors('standard') == set()
    assert PL.ancestors('light-strip-nodev') == {'standard-nodev', 'light-strip', 'standard'}
    assert len(PL.ancestors('light-strip-chinless-upperkeys-nodev')) == 15
    o = PL.parse([])
    o.cpu = 12
    P = PL.plan(o)
    b = {s.build: s for s in P.steps if s.kind == 'build'}
    assert b['light-strip-nodev'].share_cands == {'bottom_keys': ['light-strip', 'standard', 'standard-nodev'],
                                                  'strip': ['light-strip']}
    assert 'strip' not in b['light-strip'].share_cands and not b['standard'].share_cands
    m = {s.build: s for s in P.steps if s.kind == 'mechanics'}
    assert not m['standard'].mech_cands and not m['light-strip-chinless'].mech_cands
    assert m['standard-upperkeys'].mech_cands == ['light-strip', 'standard']
    assert m['chinless-nodev'].mech_cands == ['light-strip-chinless', 'chinless']
    assert sum(s.kind == 'guard' for s in P.steps) == 32
    o2 = PL.parse(['--unshared'])
    o2.cpu = 12
    P2 = PL.plan(o2)
    assert not any(s.kind == 'guard' or s.share_cands or s.mech_cands for s in P2.steps)


DEPS_PARAMS = '''A = 1
B = 2
C = 3
D = 4
'''
DEPS_M = '''import params as P
K = P.D * 2
tub_s = P.C


def f(tub_s):
    return tub_s + P.A + g()


def g():
    import params
    return K


def h():
    return [x for x in (P.B,)]
'''


def test_deps_closure():
    """deps.params_read: a local name shadows a module name, a module-level constant derived from params counts."""
    import deps, tempfile
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / 'params.py').write_text(DEPS_PARAMS)
        (d / 'm.py').write_text(DEPS_M)
        names, _ = deps.params_read(['m.f'], src=d)
        assert names == ['A', 'D'], names               # not C (f's own tub_s shadows it), D through K
        names, _ = deps.params_read(['m.h'], src=d)
        assert names == ['B'], names


def test_audit_mech():
    """--unshared --verify: mechanics.py's mechanics.json of a sharer is compared with mechanics_share.py's entries of
    the same inputs (parts, code, environment, owners' files on disk): equal passes, a difference fails the run, and
    an entry of other inputs is not compared (the build is named as not audited)."""
    import json, tempfile, cache
    old = PL.ROOT, PL.CACHE
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        PL.ROOT, PL.CACHE = root, root / 'cache'
        try:
            for b, body in (('standard-nodev', b'{"mine": 1}'), ('standard', b'{"owner": 1}')):
                (root / 'out' / b).mkdir(parents=True)
                (root / 'out' / b / 'mechanics.json').write_bytes(body)
            P = PL.Pipeline(PL.parse(['--unshared', '--verify']))
            s = PL.Step('mechanics', 'standard-nodev')
            static = {'format': 1, 'root': str(root), 'env': {'python': 'x'}, 'hardware': 'hw'}
            s.parts = {**static, 'step': 'mechanics', 'build': 'standard-nodev', 'args': [], 'sources': {},
                       'upstream': {'out/standard-nodev/tub.stl': 'tub'}}
            s.status = 'ran'
            P.steps = [s]
            want = {m: cache.sha((PL.SRC / f'{m}.py').read_bytes()) for m in cache.closure('mechanics_share')
                    if m not in PL.NOT_CODE}

            def entry(name, out, owner=cache.sha(b'{"owner": 1}'), sources=want):
                e = {'parts': {**static, 'step': 'mechanics', 'build': 'standard-nodev', 'sources': sources,
                               'args': ['--sks-from', 'standard'],
                               'upstream': {'out/standard-nodev/tub.stl': 'tub', 'out/standard/mechanics.json': owner}},
                     'outputs': {'out/standard-nodev/mechanics.json': {'sha': cache.sha(out)}}, 'created': name}
                d = P.entry_dir(s)
                d.mkdir(parents=True, exist_ok=True)
                (d / f'{name}.json').write_text(json.dumps(e))
            entry('other-owner', b'{"other": 1}', owner='x')        # read another owner file: not compared
            entry('other-code', b'{"other": 1}', sources={})          # older code: not compared
            P.audit_mech()
            assert not P.failed
            entry('same', b'{"mine": 1}')
            P.audit_mech()
            assert not P.failed
            entry('differs', b'{"mine": 2}')
            P.audit_mech()
            assert len(P.failed) == 1 and 'differs' in P.failed[0], P.failed
        finally:
            PL.ROOT, PL.CACHE = old


if __name__ == '__main__':
    t0 = time.time()
    real = PL.free_commit
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            t = time.time()
            fn()
            PL.free_commit = real
            print(f'PASS {name} ({time.time() - t:.1f}s)', flush=True)
    print(f'all passed ({time.time() - t0:.0f}s)')
