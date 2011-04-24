"""process.py - Process spawning module."""

import gc
import subprocess
import sys
import encoding

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

    def _exec(self):
        """Spawns the process, and returns its stdout.
        (NOTE: separate function to make python2.4 exception syntax happy)
        """
        try:
            # Cannot spawn processes with PythonW/Win32 unless stdin and
            # stderr are redirected to a pipe as well.
            self._proc = subprocess.Popen(self._args, stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            self._proc.stdin.close()
            self._proc.stderr.close()
            return self._proc.stdout
        except Exception, ex:
            cmd = len(self._args) > 0 and self._args[0] or "<invalid>"
            print_( _('! Error spawning process "%(command)s": %(error)s') %
                { 'command' : cmd, 'error' : encoding.to_unicode(str(ex)) } )
            print_( _('! "%s" must be on your system PATH to be found.') % cmd )
            return None

    def spawn(self):
        """Spawn the process defined by the args in __init__(). Return a
        file-like object linked to the spawned process' stdout.
        """
        try:
            gc.disable() # Avoid Python issue #1336!
            return self._exec()
        finally:
            gc.enable()

    def wait(self):
        """Wait for the process to terminate."""
        if self._proc is None:
            raise Exception('Process not spawned.')
        return self._proc.wait()


# vim: expandtab:sw=4:ts=4
