import io
from threading import Lock

_IOLock=Lock()

class LockedFileIO(io.FileIO):

    def read(self,*args,**kwargs):
        with _IOLock:
            return super().read(*args,**kwargs)

    def readinto(self,*args,**kwargs):
        with _IOLock:
            return super().readinto(*args,**kwargs)

    def readline(self,*args,**kwargs):
        with _IOLock:
            return super().readline(*args,**kwargs)

    def readlines(self,*args,**kwargs):
        with _IOLock:
            return super().readlines(*args,**kwargs)

    def readall(self):
        with _IOLock:
            return super().readall()

    def write(self,*args,**kwargs):
        with _IOLock:
            return super().write(*args,**kwargs)

    def writelines(self,*args,**kwargs):
        with _IOLock:
            return super().writelines(*args,**kwargs)

    def seek(self,*args,**kwargs):
        with _IOLock:
            return super().seek(*args,**kwargs)

    def tell(self):
        with _IOLock:
            return super().tell()

    def flush(self):
        with _IOLock:
            return super().flush()

    def truncate(self,*args,**kwargs):
        with _IOLock:
            return super().truncate(*args,**kwargs)
