# -*- coding: utf-8 -*-

""" RAR archive extractor. """

from mcomix import process
from mcomix.archive import archive_base

# Filled on-demand by RarArchive
_rar_executable = -1

class RarArchive(archive_base.ExternalExecutableArchive):
    """ RAR file extractor using the unrar/rar executable. """

    def _get_executable(self):
        return self._find_unrar_executable()

    def _get_list_arguments(self):
        return [u'vb', u'-p-', u'--']

    def _get_extract_arguments(self):
        return [u'p', u'-inul', u'-@', u'-p-', u'--']

    @staticmethod
    def _find_unrar_executable():
        """ Tries to start rar/unrar, and returns either 'rar' or 'unrar' if
        one of them was started successfully.
        Returns None if neither could be started. """
        global _rar_executable
        if _rar_executable == -1:
            _rar_executable = process.find_executable((u'unrar', u'rar'))
        return _rar_executable

    @staticmethod
    def is_available():
        return bool(RarArchive._find_unrar_executable())

# vim: expandtab:sw=4:ts=4
