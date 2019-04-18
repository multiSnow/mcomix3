import os
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

    class MountFailed(Exception):
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
        self._cmdthread=None
        self._errno=0

        self._tmpdir=None
        self.mountpoint=None
        self.sourcepath=None

    def _mountcmd(self,*cmd):
        self._mounted=True

        self._errno=subprocess.run(cmd).returncode

        if self._tmpdir:
            self._tmpdir.cleanup()
            self._tmpdir=None
        self.mountpoint=None
        self._mounted=False

    def mount(self,source,options=[],mountpoint=None):
        with self._lock:

            if self._mounted or self._cmdthread:
                raise self.AlreadyMounted
            if not os.path.exists(source):
                raise FileNotFoundError

            if mountpoint is None:
                self._tmpdir=tempfile.TemporaryDirectory(prefix='mountpoint')
                self.mountpoint=self._tmpdir.name
            elif not os.path.exists(mountpoint):
                raise FileNotFoundError(mountpoint)
            elif not os.path.isdir(mountpoint):
                raise NotADirectoryError(mountpoint)
            elif os.listdir(mountpoint):
                raise self.NotEmptyMountPoint(mountpoint)
            else:
                self._tmpdir=None
                self.mountpoint=mountpoint

            self._errno=0
            cmd=[self._cmd,'-f']
            option=','.join(options)
            if option:
                cmd.append('-o')
                cmd.append(option)
            cmd.append(source)
            cmd.append(self.mountpoint)

            self._cmdthread=threading.Thread(
                target=self._mountcmd,args=cmd,daemon=True)
            self._cmdthread.start()

            while not os.path.ismount(self.mountpoint):
                if self._errno:
                    raise self.MountFailed(source,option,self._errno)
                self._cmdthread.join(.5)
                if not self._cmdthread.is_alive():
                    break

            return self

    def unmount(self):
        with self._lock:
            if self._errno:
                raise self.MountFailed(self._errno)
            if not self._mounted:
                raise self.NotMounted
            if not os.path.ismount(self.mountpoint):
                raise self.NotMounted(self.mountpoint)

            subprocess.run((self._fusermount,'-u',self.mountpoint)).returncode
            self._cmdthread.join()
            self._cmdthread=None

    def __call__(self,source,options=[],mountpoint=None):
        return self.mount(source,options=options,
                          mountpoint=mountpoint)

    def __enter__(self):
        return self

    def __exit__(self,etype,value,tb):
        self.unmount()

if __name__=='__main__':
    exit(0)
