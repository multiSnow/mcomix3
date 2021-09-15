'''process.py - Process spawning module.'''

import gc
import sys
import os
import shutil
import subprocess
from threading import Thread

from mcomix import log
from mcomix import i18n



NULL = subprocess.DEVNULL
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if 'win32' == sys.platform else 0
FNAME_ENCODING = sys.getfilesystemencoding()

# Convert argument vector to system's file encoding where necessary
# to prevent automatic conversion when appending Unicode strings
# to byte strings later on.
def _fix_args(args):
    return [c.encode(FNAME_ENCODING) if isinstance(c, str) else c
            for c in args]

# Cannot spawn processes with PythonW/Win32 unless stdin
# and stderr are redirected to a pipe/devnull as well.
def call(args, **kwds):
    params=dict(stdout=NULL,stderr=NULL,
                creationflags=CREATIONFLAGS)
    params.update(kwds)
    return not subprocess.run(_fix_args(args), **params).returncode

def popen(args, **kwds):
    params=dict(stdout=PIPE,stderr=NULL,
                creationflags=CREATIONFLAGS)
    params.update(kwds)
    return subprocess.Popen(_fix_args(args), **params)

def call_thread(args, **kwds):
    # call command in thread, so drop std* and set no buffer
    params=dict(stdout=NULL,stderr=NULL,bufsize=0,
                creationflags=CREATIONFLAGS)
    params.update(kwds)
    thread=Thread(target=subprocess.run,args=(_fix_args(args),),kwargs=params,daemon=True)
    thread.start()

if 'win32' == sys.platform:
    _exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

def find_executable(candidates, workdir=None, is_valid_candidate=None):
    ''' Find executable in path.

    Return an absolute path to a valid executable or None.

    <workdir> default to the current working directory if not set.

    <is_valid_candidate> is an optional function that must return True
    if the path passed in argument is a valid candidate (to check for
    version number, symlinks to an unsupported variant, etc...).

    If a candidate has a directory component,
    it will be checked relative to <workdir>.
    '''

    if callable(is_valid_candidate):
        is_valid = is_valid_candidate
    else:
        is_valid = lambda exe: True

    for name in candidates:
        path = shutil.which(name)
        if not path:
            continue
        if not is_valid(path):
            continue
        return name

    return None


def Win32Popen(cmd):
    ''' Spawns a new process on Win32. cmd is a list of parameters.
    This method's sole purpose is calling CreateProcessW, not
    CreateProcessA as it is done by subprocess.Popen. '''
    import ctypes

    # Declare common data types
    DWORD = ctypes.c_uint
    WORD = ctypes.c_ushort
    LPTSTR = ctypes.c_wchar_p
    LPBYTE = ctypes.POINTER(ctypes.c_ubyte)
    HANDLE = ctypes.c_void_p

    class StartupInfo(ctypes.Structure):
        _fields_ = [('cb', DWORD),
                    ('lpReserved', LPTSTR),
                    ('lpDesktop', LPTSTR),
                    ('lpTitle', LPTSTR),
                    ('dwX', DWORD),
                    ('dwY', DWORD),
                    ('dwXSize', DWORD),
                    ('dwYSize', DWORD),
                    ('dwXCountChars', DWORD),
                    ('dwYCountChars', DWORD),
                    ('dwFillAttribute', DWORD),
                    ('dwFlags', DWORD),
                    ('wShowWindow', WORD),
                    ('cbReserved2', WORD),
                    ('lpReserved2', LPBYTE),
                    ('hStdInput', HANDLE),
                    ('hStdOutput', HANDLE),
                    ('hStdError', HANDLE)]
    class ProcessInformation(ctypes.Structure):
        _fields_ = [('hProcess', HANDLE),
                    ('hThread', HANDLE),
                    ('dwProcessId', DWORD),
                    ('dwThreadId', DWORD)]

    LPSTRARTUPINFO = ctypes.POINTER(StartupInfo)
    LPROCESS_INFORMATION = ctypes.POINTER(ProcessInformation)
    ctypes.windll.kernel32.CreateProcessW.argtypes = [LPTSTR, LPTSTR,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool, DWORD,
        ctypes.c_void_p, LPTSTR, LPSTRARTUPINFO, LPROCESS_INFORMATION]
    ctypes.windll.kernel32.CreateProcessW.restype = ctypes.c_bool

    # Convert list of arguments into a single string
    cmdline = subprocess.list2cmdline(cmd)
    buffer = ctypes.create_unicode_buffer(cmdline)

    # Resolve executable path.
    exe = find_executable((cmd[0],))

    # Some required structures for the method call...
    startupinfo = StartupInfo()
    ctypes.memset(ctypes.addressof(startupinfo), 0, ctypes.sizeof(startupinfo))
    startupinfo.cb = ctypes.sizeof(startupinfo)
    processinfo = ProcessInformation()

    # Spawn new process
    success = ctypes.windll.kernel32.CreateProcessW(exe, buffer,
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
