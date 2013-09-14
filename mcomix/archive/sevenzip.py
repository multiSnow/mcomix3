# -*- coding: utf-8 -*-

""" 7z archive extractor. """

from mcomix import process
from mcomix.archive import archive_base

# Filled on-demand by SevenZipArchive
_7z_executable = -1

class SevenZipArchive(archive_base.ExternalExecutableArchive):
    """ 7z file extractor using the 7z executable. """

    STATE_HEADER, STATE_LISTING, STATE_FOOTER = 1, 2, 3

    def __init__(self, archive):
        super(SevenZipArchive, self).__init__(archive)

        #: Indicates which part of the file listing has been read
        self._state = SevenZipArchive.STATE_HEADER

    def _get_executable(self):
        return SevenZipArchive._find_7z_executable()

    def _get_list_arguments(self):
        return [u'l', u'-p', u'--']

    def _get_extract_arguments(self):
        return [u'x', u'-so', u'-p', u'--']

    def _parse_list_output_line(self, line):
        """ Start parsing after the first delimiter (bunch of - characters),
        and end when delimiters appear again. Format:
        Date <space> Time <space> Attr <space> Size <space> Compressed <space> Name"""
        if line.startswith('----'):
            if self._state == SevenZipArchive.STATE_HEADER:
                # First delimiter reached, start reading from next line
                self._state = SevenZipArchive.STATE_LISTING
            elif self._state == SevenZipArchive.STATE_LISTING:
                # Last delimiter read, stop reading from now on
                self._state = SevenZipArchive.STATE_FOOTER

            return None
        else:
            if self._state == SevenZipArchive.STATE_LISTING:
                # 7z occasionally does not include all columns when printing
                # the listing, so splitting columns by spaces is unreliable.
                # Use hardcoded start point by characters instead.
                return line[53:]
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
