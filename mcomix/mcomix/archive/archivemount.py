from mcomix.archive import archive_base

class ArchivemountArchive(archive_base.MountArchive):
    def __init__(self,archive):
        super(ArchivemountArchive,self).__init__(
            archive,'archivemount',
            options=['readonly','auto_cache'])

    @staticmethod
    def is_available():
        return archive_base.MountArchive._is_available('archivemount')
