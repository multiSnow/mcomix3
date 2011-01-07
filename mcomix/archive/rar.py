# -*- encoding: utf-8 -*-

""" RAR archive extractor. """

from mcomix import process
from mcomix.archive import archive_base
from mcomix.archive import rarfile

class RarExecArchive(archive_base.ExternalExecutableArchive):
    """ RAR file extractor using the unrar/rar executable. """

    def _get_executable(self):
        return _executable

    def _get_list_arguments(self):
        return [u'vb', u'--']

    def _get_extract_arguments(self):
        return [u'p', u'-inul', u'-p-', u'--']

    @staticmethod
    def _find_unrar_executable():
        """ Tries to start rar/unrar, and returns either 'rar' or 'unrar' if
        one of them was started successfully.
        Returns None if neither could be started. """
        for command in (u'rar', u'unrar'):
            proc = process.Process([command])
            fd = proc.spawn()
            if fd is not None:
                fd.close()
                return command

        return None

    @staticmethod
    def is_available():
        return bool(_executable)

_executable = RarExecArchive._find_unrar_executable()

class RarArchive(archive_base.BaseArchive):
    """ RAR file extractor using libunrar.so/unrar.dll.
    Uses command line version of rar as fallback. """

    def __init__(self, archive):
        super(RarArchive, self).__init__(archive)

        if rarfile.UnrarDll.is_available():
            self.rar = rarfile.UnrarDll(archive)
        else:
            self.rar = RarExecArchive(archive)

    def list_contents(self):
        return self.rar.list_contents()

    def extract(self, filename, destination_path):
        return self.rar.extract(filename, destination_path)

    def close(self):
        return self.rar.close()

    @staticmethod
    def is_available():
        return rarfile.UnrarDll.is_available() or RarExecArchive.is_available()

# vim: expandtab:sw=4:ts=4
