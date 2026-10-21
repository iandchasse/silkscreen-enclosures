"""Step processes in Windows Job Objects (pipeline.py's scheduler, 2026-10-08; no step imports this module).

The venv's python.exe is a launcher that starts the real interpreter as a child, and a slice step starts OrcaSlicer
as a grandchild, so the handle subprocess.Popen returns sees about 1 MB and no CPU time: only a job object sees the
whole step. A step is started suspended, put in its own job, then resumed, so no child escapes it. The job has no
limit but JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: when the pipeline ends (or dies), its steps end with it instead of
running on as orphans that hold their memory.

    j = Job(cmd, **popen_kwargs)      # started
    j.proc                            # the subprocess.Popen (wait/poll/returncode as usual)
    j.commit()                        # bytes of private memory (commit) the job's processes hold now
    j.stats()                         # {'peak_gb', 'cpu_s', 'procs'}: peak commit of the whole job, CPU time
    j.terminate()                     # ends every process of the job (the safety valve: our own steps only)
    j.close()

Elsewhere than Windows (or when the job cannot be made) a Job is a plain Popen and measures nothing.
physical_cores(): the number of physical cores (the scheduler's default CPU cap).
"""
import os, subprocess

WINDOWS = os.name == 'nt'
if WINDOWS:
    import ctypes
    import ctypes.wintypes as W

    _k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _ntdll = ctypes.WinDLL('ntdll')
    _psapi = ctypes.WinDLL('psapi')
    _k32.CreateJobObjectW.restype = W.HANDLE
    _k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, W.LPCWSTR)
    _k32.OpenProcess.restype = W.HANDLE

    class _IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ('ReadOps', 'WriteOps', 'OtherOps', 'ReadBytes', 'WriteBytes',
                                                      'OtherBytes')]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                    ('LimitFlags', W.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', W.DWORD),
                    ('Affinity', ctypes.c_size_t), ('PriorityClass', W.DWORD), ('SchedulingClass', W.DWORD)]

    class _EXT_LIMIT(ctypes.Structure):
        _fields_ = [('Basic', _BASIC_LIMIT), ('Io', _IO), ('ProcessMemoryLimit', ctypes.c_size_t),
                    ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t),
                    ('PeakJobMemoryUsed', ctypes.c_size_t)]

    class _BASIC_ACCT(ctypes.Structure):
        _fields_ = [('TotalUserTime', ctypes.c_longlong), ('TotalKernelTime', ctypes.c_longlong),
                    ('ThisPeriodTotalUserTime', ctypes.c_longlong), ('ThisPeriodTotalKernelTime', ctypes.c_longlong),
                    ('TotalPageFaultCount', W.DWORD), ('TotalProcesses', W.DWORD), ('ActiveProcesses', W.DWORD),
                    ('TotalTerminatedProcesses', W.DWORD)]

    class _PMC(ctypes.Structure):
        _fields_ = [('cb', W.DWORD), ('PageFaultCount', W.DWORD)] + [(n, ctypes.c_size_t) for n in (
            'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
            'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage',
            'PrivateUsage')]

    _CREATE_SUSPENDED = 0x4
    _KILL_ON_CLOSE = 0x2000
    _EXT_INFO, _ACCT_INFO, _PID_LIST = 9, 1, 3


class Job:
    def __init__(self, cmd, **kw):
        self.job = None
        if not WINDOWS:
            self.proc = subprocess.Popen(cmd, **kw)
            return
        job = _k32.CreateJobObjectW(None, None)
        if job:
            e = _EXT_LIMIT()
            e.Basic.LimitFlags = _KILL_ON_CLOSE
            _k32.SetInformationJobObject(W.HANDLE(job), _EXT_INFO, ctypes.byref(e), ctypes.sizeof(e))
        kw['creationflags'] = kw.get('creationflags', 0) | (_CREATE_SUSPENDED if job else 0)
        self.proc = subprocess.Popen(cmd, **kw)
        if job:
            if _k32.AssignProcessToJobObject(W.HANDLE(job), W.HANDLE(int(self.proc._handle))):
                self.job = job
            else:                                       # (a parent job that forbids it): run unmeasured
                _k32.CloseHandle(W.HANDLE(job))
            _ntdll.NtResumeProcess(W.HANDLE(int(self.proc._handle)))

    def pids(self):
        if not self.job:
            return [self.proc.pid]

        class L(ctypes.Structure):
            _fields_ = [('n', W.DWORD), ('m', W.DWORD), ('ids', ctypes.c_size_t * 256)]
        lst = L()
        if not _k32.QueryInformationJobObject(W.HANDLE(self.job), _PID_LIST, ctypes.byref(lst), ctypes.sizeof(lst), None):
            return []
        return [int(lst.ids[i]) for i in range(min(lst.m, 256))]

    def commit(self):
        """Bytes of private memory (commit charge) the job's processes hold now (0 when unmeasured)."""
        if not WINDOWS:
            return 0
        tot = 0
        for pid in self.pids():
            h = _k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                continue
            c = _PMC()
            c.cb = ctypes.sizeof(_PMC)
            if _psapi.GetProcessMemoryInfo(W.HANDLE(h), ctypes.byref(c), c.cb):
                tot += c.PrivateUsage
            _k32.CloseHandle(W.HANDLE(h))
        return tot

    def stats(self):
        """{'peak_gb': the job's peak commit, 'cpu_s': user + kernel time of all its processes, 'procs'}; {} when
        unmeasured."""
        if not self.job:
            return {}
        e, a = _EXT_LIMIT(), _BASIC_ACCT()
        _k32.QueryInformationJobObject(W.HANDLE(self.job), _EXT_INFO, ctypes.byref(e), ctypes.sizeof(e), None)
        _k32.QueryInformationJobObject(W.HANDLE(self.job), _ACCT_INFO, ctypes.byref(a), ctypes.sizeof(a), None)
        return {'peak_gb': round(e.PeakJobMemoryUsed / 1e9, 3), 'cpu_s': round((a.TotalUserTime + a.TotalKernelTime) / 1e7, 1),
                'procs': int(a.TotalProcesses)}

    def terminate(self):
        if self.job:
            _k32.TerminateJobObject(W.HANDLE(self.job), 1)
        else:
            self.proc.terminate()

    def close(self):
        if self.job:
            _k32.CloseHandle(W.HANDLE(self.job))
            self.job = None


def physical_cores():
    """The machine's physical cores (logical processors / 2 when they cannot be counted)."""
    if WINDOWS:
        try:
            n = W.DWORD(0)
            _k32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(n))    # RelationProcessorCore: the size
            buf = (ctypes.c_byte * n.value)()
            if _k32.GetLogicalProcessorInformationEx(0, buf, ctypes.byref(n)):
                cores, off = 0, 0
                while off < n.value:
                    size = ctypes.c_uint32.from_buffer(buf, off + 4).value  # (Relationship, Size, ...)
                    cores += 1
                    off += size
                if cores:
                    return cores
        except (OSError, AttributeError, ValueError):
            pass
    return max(1, (os.cpu_count() or 2) // 2)
