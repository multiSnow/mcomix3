"""process.py - Process spawning module."""

import gc
import sys
import os
from distutils import spawn

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

def _get_creationflags():
    if 'win32' == sys.platform:
        # Do not create a console window.
        return 0x08000000
    else:
        return 0

# Cannot spawn processes with PythonW/Win32 unless stdin
# and stderr are redirected to a pipe/devnull as well.
def call(args, stdin=NULL, stdout=NULL, stderr=NULL):
    return 0 == subprocess.call(_fix_args(args), stdin=stdin,
                                stdout=stdout, stderr=stderr,
                                creationflags=_get_creationflags())

def popen(args, stdin=NULL, stdout=PIPE, stderr=NULL):
    if not _using_subprocess32:
        gc.disable() # Avoid Python issue #1336!
    try:
        return subprocess.Popen(_fix_args(args), stdin=stdin,
                                stdout=stdout, stderr=stderr,
                                creationflags=_get_creationflags())
    finally:
        if not _using_subprocess32:
            gc.enable()


if 'win32' == sys.platform:
    _exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

def find_executable(candidates, workdir=None):
    """ Find executable in path.

    Return an absolute path to a valid executable or None.

    <workdir> default to the current working directory if not set.

    If a candidate has a directory component,
    it will be checked relative to <workdir>.

    On Windows:

    - '.exe' will be appended to each candidate if not already

    - MComix executable directory is prepended to the path on Windows
      (to support embedded tools/executables in the distribution).

    - <workdir> will be inserted first in the path.

    On Unix:

    - a valid candidate must have execution right

    """
    if workdir is None:
        workdir = os.getcwd()
    workdir = os.path.abspath(workdir)

    search_path = os.environ['PATH'].split(os.pathsep)
    if 'win32' == sys.platform:
        if workdir is not None:
            search_path.insert(0, workdir)
        search_path.insert(0, _exe_dir)

    valid_exe = lambda exe: \
            os.path.isfile(exe) and \
            os.access(exe, os.R_OK|os.X_OK)

    for name in candidates:

        # On Windows, must end with '.exe'
        if 'win32' == sys.platform:
            if not name.endswith('.exe'):
                name = name + '.exe'

        # Absolute path?
        if os.path.isabs(name):
            if valid_exe(name):
                return name

        # Does candidate have a directory component?
        elif os.path.dirname(name):
            # Yes, check relative to working directory.
            path = os.path.normpath(os.path.join(workdir, name))
            if valid_exe(path):
                return path

        # Look in search path.
        else:
            for dir in search_path:
                path = os.path.abspath(os.path.join(dir, name))
                if valid_exe(path):
                    return path

    return None


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

    # Resolve executable path.
    exe = find_executable((cmd[0],))

    # Some required structures for the method call...
    startupinfo = StartupInfo()
    ctypes.memset(ctypes.addressof(startupinfo), 0, ctypes.sizeof(startupinfo))
    # Do not create a console window.
    startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
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
