import shutil
import subprocess
import tempfile
import threading

class MountManager:

    class CommandNotFound(Exception):
        pass

    class AlreadyMounted(Exception):
        pass

    class NotMounted(Exception):
        pass

    class NotEmptyMountPoint(Exception):
        pass

    def __init__(self,cmd):
        self._cmd=shutil.which(cmd)
        self._fusermount=shutil.which('fusermount')

        if not self._cmd:
            raise self.CommandNotFound('{} not found.'.format(self._cmd))
        if not self._fusermount:
            raise self.CommandNotFound('{} not found.'.format(self._fusermount))

        self._mounted=False
        self._lock=threading.Lock()

        self._tmpdir=None
        self.mountpoint=None
        self.sourcepath=None

    def mount(self,options=(),source=None,mountpoint=None):
        with self._lock:
            if self._mounted:
                raise self.AlreadyMounted
            self._mounted=True
            return self

    def unmount(self):
        with self._lock:
            if not self._mounted:
                raise self.NotMounted
            self._mounted=False

    def __call__(self,options=(),source=None,mountpoint=None):
        return self.mount(options=options,
                          source=source,mountpoint=mountpoint)

    def __enter__(self):
        return self

    def __exit__(self,etype,value,tb):
        self.unmount()

if __name__=='__main__':
    exit(0)
