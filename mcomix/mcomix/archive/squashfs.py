import os
import shutil

from mcomix.archive import archive_base

class SquashfsArchive(archive_base.MountArchive):
    def __init__(self,archive):
        super(SquashfsArchive,self).__init__(archive,'squashfuse')

    @staticmethod
    def is_available():
        return shutil.which('squashfuse') and shutil.which('fusermount')
