import shutil

from mcomix.archive import archive_base

class ArchivemountArchive(archive_base.MountArchive):
    def __init__(self,archive):
        super(ArchivemountArchive,self).__init__(
            archive,'archivemount',
            options=['readonly'])

    @staticmethod
    def is_available():
        return shutil.which('archivemount') and shutil.which('fusermount')
