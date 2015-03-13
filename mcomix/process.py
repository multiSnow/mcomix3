"""process.py - Process spawning module."""

import gc
import sys
import os

from mcomix import log
from mcomix import i18n

try:
    import subprocess32 as subprocess
    _using_subprocess32 = True
except ImportError:
    log.warning('subprocess32 not available! using subprocess')
    import subprocess
    _using_subprocess32 = False


NULL = open(os.devnull, 'r+b')
PIPE = subprocess.PIPE

# Convert argument vector to system's file encoding where necessary
# to prevent automatic conversion when appending Unicode strings
# to byte strings later on.
def _fix_args(args):
    fixed_args = []
    for arg in args:
        if isinstance(arg, unicode):
            fixed_args.append(arg.encode(sys.getfilesystemencoding()))
        else:
            fixed_args.append(arg)
    return fixed_args

# Cannot spawn processes with PythonW/Win32 unless stdin
# and stderr are redirected to a pipe/devnull as well.
def call(args, stdin=NULL, stdout=NULL, stderr=NULL):
    return 0 == subprocess.call(_fix_args(args), stdin=stdin,
                                stdout=stdout, stderr=stderr)

def popen(args, stdin=NULL, stdout=PIPE, stderr=NULL):
    if not _using_subprocess32:
        gc.disable() # Avoid Python issue #1336!
    try:
        return subprocess.Popen(_fix_args(args), stdin=stdin,
                                stdout=stdout, stderr=stderr)
    finally:
        if not _using_subprocess32:
            gc.enable()


def Win32Popen(cmd):
    """ Spawns a new process on Win32. cmd is a list of parameters. 
    This method's sole purpose is calling CreateProcessW, not
    CreateProcessA as it is done by subprocess.Popen. """
    import ctypes

    # Declare common data types
    DWORD = ctypes.c_uint
    WORD = ctypes.c_ushort
    LPTSTR = ctypes.c_wchar_p
    LPBYTE = ctypes.POINTER(ctypes.c_ubyte)
    HANDLE = ctypes.c_void_p

    class StartupInfo(ctypes.Structure):
        _fields_ = [("cb", DWORD),
            ("lpReserved", LPTSTR),
            ("lpDesktop", LPTSTR),
            ("lpTitle", LPTSTR),
            ("dwX", DWORD),
            ("dwY", DWORD),
            ("dwXSize", DWORD),
            ("dwYSize", DWORD),
            ("dwXCountChars", DWORD),
            ("dwYCountChars", DWORD),
            ("dwFillAttribute", DWORD),
            ("dwFlags", DWORD),
            ("wShowWindow", WORD),
            ("cbReserved2", WORD),
            ("lpReserved2", LPBYTE),
            ("hStdInput", HANDLE),
            ("hStdOutput", HANDLE),
            ("hStdError", HANDLE)]
    class ProcessInformation(ctypes.Structure):
        _fields_ = [("hProcess", HANDLE),
            ("hThread", HANDLE),
            ("dwProcessId", DWORD),
            ("dwThreadId", DWORD)]

    LPSTRARTUPINFO = ctypes.POINTER(StartupInfo)
    LPROCESS_INFORMATION = ctypes.POINTER(ProcessInformation)
    ctypes.windll.kernel32.CreateProcessW.argtypes = [LPTSTR, LPTSTR,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool, DWORD,
        ctypes.c_void_p, LPTSTR, LPSTRARTUPINFO, LPROCESS_INFORMATION]
    ctypes.windll.kernel32.CreateProcessW.restype = ctypes.c_bool

    # Convert list of arguments into a single string
    cmdline = subprocess.list2cmdline(cmd)
    buffer = ctypes.create_unicode_buffer(cmdline)

    # Some required structures for the method call...
    startupinfo = StartupInfo()
    ctypes.memset(ctypes.addressof(startupinfo), 0, ctypes.sizeof(startupinfo))
    startupinfo.cb = ctypes.sizeof(startupinfo)
    processinfo = ProcessInformation()

    # Spawn new process
    success = ctypes.windll.kernel32.CreateProcessW(cmd[0], buffer,
            None, None, False, 0, None, None, ctypes.byref(startupinfo),
            ctypes.byref(processinfo))

    if success:
        ctypes.windll.kernel32.CloseHandle(processinfo.hProcess)
        ctypes.windll.kernel32.CloseHandle(processinfo.hThread)
        return processinfo.dwProcessId
    else:
        raise ctypes.WinError(ctypes.GetLastError(),
                i18n.to_unicode(ctypes.FormatError()))


# vim: expandtab:sw=4:ts=4
