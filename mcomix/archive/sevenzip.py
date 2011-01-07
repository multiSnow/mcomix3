# -*- encoding: utf-8 -*-

""" 7z archive extractor. """

from mcomix import process
from mcomix import encoding
from mcomix.archive import archive_base

class SevenZipArchive(archive_base.ExternalExecutableArchive):
    """ 7z file extractor using the 7z executable. """

    def _get_executable(self):
        return _executable

    def _get_list_arguments(self):
        return [u'l', u'-slt', u'--']

    def _get_extract_arguments(self):
        return [u'x', u'-so', u'--']

    def _parse_list_output_line(self, line):
        if line.startswith('Path = '):
            return line[len('Path = '):]
        else:
            return None

    @staticmethod
    def _find_7z_executable():
        """ Tries to start 7z, and returns either '7z' if
        it was started successfully or None otherwise. """
        proc = process.Process([u'7z'])
        fd = proc.spawn()
        if fd is not None:
            fd.close()
            return u'7z'
        else:
            return None

    @staticmethod
    def is_available():
        return bool(_executable)

_executable = SevenZipArchive._find_7z_executable()

# vim: expandtab:sw=4:ts=4
