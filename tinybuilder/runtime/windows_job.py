"""Windows-owned process tree, using an unnamed non-inheritable Job Object."""
import ctypes
import time
from ctypes import wintypes

from .errors import RuntimeFailure


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits), ("IoInfo", _IOCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _Accounting(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int64) for name in (
        "TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime"
    )] + [(name, wintypes.DWORD) for name in (
        "TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses")]


class WindowsJob:
    def __init__(self):
        self._api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "QueryInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self._api, name)
            fn.argtypes, fn.restype = args, result
        self._handle = self._api.CreateJobObjectW(None, None)
        if not self._handle:
            self._fail("process_spawn", "job_create")
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self._api.SetInformationJobObject(self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            code = ctypes.get_last_error()
            self.close()
            raise RuntimeFailure("process_spawn", stage="job_configure", os_code=code)

    @staticmethod
    def _fail(kind, stage):
        raise RuntimeFailure(kind, stage=stage, os_code=ctypes.get_last_error())

    def attach(self, process):
        # CPython Popen retains the exact native process handle. Never reopen
        # by PID (which can be recycled). Assignment occurs just after launch.
        if not self._api.AssignProcessToJobObject(self._handle, int(process._handle)):
            self._fail("process_spawn", "job_assign")

    def terminate(self, timeout):
        if not self._api.TerminateJobObject(self._handle, 1):
            self._fail("cleanup_failed", "job_terminate")
        deadline = time.monotonic() + timeout
        while True:
            accounting = _Accounting()
            if not self._api.QueryInformationJobObject(self._handle, 1, ctypes.byref(accounting),
                                                       ctypes.sizeof(accounting), None):
                self._fail("cleanup_failed", "job_query")
            if accounting.ActiveProcesses == 0:
                return
            if time.monotonic() >= deadline:
                raise RuntimeFailure("cleanup_failed", stage="job_wait")
            time.sleep(0.02)

    def close(self):
        if self._handle:
            if not self._api.CloseHandle(self._handle):
                self._fail("cleanup_failed", "job_close")
            self._handle = None
