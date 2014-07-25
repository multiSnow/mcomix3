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

NULL = open(os.devnull, 'wb')

class Process:

    """The subprocess and popen2 modules in Python are broken (see issue
    #1336). The problem (i.e. complete crash) they can cause happen fairly
    often (once is too often) in MComix when calling "rar" or "unrar" to
    extract specific files from archives. We roll our own very simple
    process spawning module here instead.
    """
    # TODO: I can no longer reproduce the issue. Check if this version of
    # process.py still solves it.

    def __init__(self, args):
        """Setup a Process where <args> is a sequence of arguments that defines
        the process, e.g. ['ls', '-a'].
        """
        # Convert argument vector to system's file encoding where necessary
        # to prevent automatic conversion when appending Unicode strings
        # to byte strings later on.
        self._args = []
        for arg in args:
            if isinstance(arg, unicode):
                self._args.append(arg.encode(sys.getfilesystemencoding()))
            else:
                self._args.append(arg)

        self._proc = None

    def _exec(self, stdin, stderr):
        """Spawns the process, and returns its stdout.
        (NOTE: separate function to make python2.4 exception syntax happy)
        """
        try:
            self._proc = subprocess.Popen(self._args, stdout=subprocess.PIPE,
                    stdin=stdin, stderr=stderr,
                    startupinfo=self._startupinfo())
            return self._proc.stdout
        except Exception, ex:
            cmd = len(self._args) > 0 and self._args[0] or "<invalid>"
            log.info((
                _('! Error spawning process "%(command)s": %(error)s.')
                + u' '
                + _('"%(command)s" must be on your system PATH to be found.')) %
                { 'command' : unicode(cmd, errors='replace'),
                  'error' : unicode(str(ex), errors='replace')})
            return None

    def _startupinfo(self):
        """ Creates a STARTUPINFO structure on Windows (to hide spawned
        unextract windows). Does nothing on other platforms. """
        if sys.platform == 'win32':
            info = subprocess.STARTUPINFO()
            STARTF_USESHOWWINDOW = 0x1
            SW_HIDE = 0x0
            info.dwFlags = STARTF_USESHOWWINDOW
            info.wShowWindow = SW_HIDE
            return info
        else:
            return None

    # Cannot spawn processes with PythonW/Win32 unless stdin and
    # stderr are redirected to a pipe/devnull as well.
    def spawn(self, stdin=subprocess.PIPE, stderr=NULL):
        """Spawn the process defined by the args in __init__(). Return a
        file-like object linked to the spawned process' stdout.
        """
        try:
            if not _using_subprocess32:
                gc.disable() # Avoid Python issue #1336!
            return self._exec(stdin, stderr)
        finally:
            if not _using_subprocess32:
                gc.enable()

    def wait(self):
        """Wait for the process to terminate."""
        if self._proc is None:
            raise Exception('Process not spawned.')
        return self._proc.wait()

    def communicate(self, input=None):
        """ Buffer all output from the kernel pipe buffer
        before returning a tuple (stdoutdata, stderrdata). """
        return self._proc.communicate(input)

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
