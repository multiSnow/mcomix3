import io
from threading import Lock

_IOLock=Lock()

class LockedFileIO(io.BytesIO):
    def __init__(self,path):
        with _IOLock:
            with open(path,mode='rb') as f:
                super().__init__(f.read())
