"""process.py - Process spawning module."""

import gc
import subprocess

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
        self._args = args
        self._proc = None
    
    def _exec(self):
        """Spawns the process, and returns its stdout.
        (NOTE: separate function to make python2.4 exception syntax happy)
        """
        try:
            self._proc = subprocess.Popen(self._args, stdout=subprocess.PIPE)
            return self._proc.stdout
        except Exception:
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

