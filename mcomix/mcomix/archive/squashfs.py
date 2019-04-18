import os
import shutil
import threading

from mcomix.archive import archive_base
from mcomix.lib import mountmanager

def walkpath(root=None):
    for name in os.listdir(root):
        path=os.path.join(root or '',name)
        if os.path.isdir(path):
            yield from map(lambda s:(name,*s),walkpath(path))
        else:
            yield name,

class SquashfsArchive(archive_base.BaseArchive):
    def __init__(self,archive):
        super(SquashfsArchive,self).__init__(archive)
        self._sqf=self.archive
        try:
            self._mgr=mountmanager.MountManager('squashfuse')
        except mountmanager.MountManager.CommandNotFound:
            self._mgr=None
            return
        self._contents=[]
        self._lock=threading.Lock()

        with self._lock:
            with self._mgr(self._sqf) as m:
                for paths in walkpath(m.mountpoint):
                    self._contents.append(os.path.join(*paths))
        self._contents.sort()

    def iter_contents(self):
        yield from self._contents

    def list_contents(self):
        return self._contents.copy()

    def is_solid(self):
        return True

    def extract(self,fn,dstdir):
        with self._lock:
            dstfile=os.path.join(dstdir,fn)
            if self._mgr.is_mounted():
                with open(os.path.join(self._mgr.mountpoint,fn),mode='rb') as src:
                    data=src.read()
            else:
                with self._mgr(self._sqf) as m:
                    with open(os.path.join(m.mountpoint,fn),mode='rb') as src:
                        data=src.read()
            with self._create_file(dstfile) as dst:
                dst.write(data)
        return dstfile

    def iter_extract(self,names,dstdir):
        with self._lock:
            self._create_directory(dstdir)
            if self._mgr.is_mounted():
                if dstdir!=self._mgr.mountpoint:
                    # umount before change mountpoint
                    self._mgr.umount()
            if not self._mgr.is_mounted():
                self._mgr.mount(self._sqf,mountpoint=dstdir)
            for name in names:
                if name in self._contents:
                    yield name

    def close(self):
        if self._mgr.is_mounted():
            self._mgr.umount()

    @staticmethod
    def is_available():
        return shutil.which('squashfuse') and shutil.which('fusermount')
