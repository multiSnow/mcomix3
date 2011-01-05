"""process.py - Process spawning module."""

import gc
import subprocess
import sys

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
            self._proc = subprocess.Popen(self._args, stdout=subprocess.PIPE)
            return self._proc.stdout
        except Exception, ex:
            print _("! Error spawning process"), str(ex)
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
