# -*- coding: utf-8 -*-

""" 7z archive extractor. """

from mcomix import process
from mcomix import encoding
from mcomix.archive import archive_base

# Filled on-demand by SevenZipArchive
_7z_executable = -1

class SevenZipArchive(archive_base.ExternalExecutableArchive):
    """ 7z file extractor using the 7z executable. """

    def _get_executable(self):
        return SevenZipArchive._find_7z_executable()

    def _get_list_arguments(self):
        return [u'l', u'-slt', u'--']

    def _get_extract_arguments(self):
        return [u'x', u'-so', u'--']

    def _parse_list_output_line(self, line):
        if line.startswith('Path = ') and not line.endswith('.7z'):
            return line[len('Path = '):]
        else:
            return None

    @staticmethod
    def _find_7z_executable():
        """ Tries to start 7z, and returns either '7z' if
        it was started successfully or None otherwise. """
        global _7z_executable
        if _7z_executable != -1:
            return _7z_executable
        else:
            proc = process.Process([u'7z'])
            fd = proc.spawn()
            if fd is not None:
                fd.close()
                _7z_executable = u'7z'
                return u'7z'
            else:
                _7z_executable = None
                return None

    @staticmethod
    def is_available():
        return bool(SevenZipArchive._find_7z_executable())


# vim: expandtab:sw=4:ts=4
